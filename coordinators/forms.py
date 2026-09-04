from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from accounts.models import UserProfile
from participants.models import Participant

from .models import CoordinationLog, ParticipantCoordinatorAssignment, SupportCoordinator
from .querysets import assigned_participants_for


class SupportCoordinatorCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)
    account_active = forms.BooleanField(label="Login enabled", required=False, initial=True)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=30, required=False)
    status = forms.ChoiceField(choices=SupportCoordinator.Status.choices)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if (
            get_user_model().objects.filter(email=email).exists()
            or SupportCoordinator.objects.filter(email=email).exists()
        ):
            raise forms.ValidationError("Email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if password1:
            pending_user = get_user_model()(
                username=cleaned_data.get("username", ""),
                email=cleaned_data.get("email", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
            )
            try:
                validate_password(password1, pending_user)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = get_user_model().objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password1"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_active=data["account_active"],
        )
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPPORT_COORDINATOR,
            phone=data["phone"],
        )
        return SupportCoordinator.objects.create(
            user=user,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            status=data["status"],
            notes=data["notes"],
        )


class SupportCoordinatorEditForm(forms.ModelForm):
    account_active = forms.BooleanField(label="Login enabled", required=False)

    class Meta:
        model = SupportCoordinator
        fields = ["email", "first_name", "last_name", "phone", "status", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["account_active"].initial = self.instance.user.is_active

    def clean_email(self):
        email = self.cleaned_data["email"]
        duplicate_user = get_user_model().objects.filter(email=email).exclude(
            pk=self.instance.user_id,
        )
        duplicate_coordinator = SupportCoordinator.objects.filter(email=email).exclude(
            pk=self.instance.pk,
        )
        if duplicate_user.exists() or duplicate_coordinator.exists():
            raise forms.ValidationError("Email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        coordinator = super().save(commit=False)
        coordinator.user.email = self.cleaned_data["email"]
        coordinator.user.first_name = self.cleaned_data["first_name"]
        coordinator.user.last_name = self.cleaned_data["last_name"]
        coordinator.user.is_active = self.cleaned_data["account_active"]
        if commit:
            coordinator.user.save()
            coordinator.save()
            profile, _ = UserProfile.objects.get_or_create(
                user=coordinator.user,
                defaults={"role": UserProfile.Role.SUPPORT_COORDINATOR},
            )
            profile.role = UserProfile.Role.SUPPORT_COORDINATOR
            profile.phone = coordinator.phone
            profile.save()
        return coordinator


class ParticipantCoordinatorAssignmentForm(forms.ModelForm):
    class Meta:
        model = ParticipantCoordinatorAssignment
        fields = ["participant", "start_date", "end_date", "is_active", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
    }

    def __init__(self, *args, **kwargs):
        self.coordinator = kwargs.pop("coordinator", None)
        super().__init__(*args, **kwargs)
        self.fields["participant"].queryset = Participant.objects.filter(
            status=Participant.Status.ACTIVE,
        ).order_by("last_name", "first_name")

    def clean(self):
        cleaned_data = super().clean()
        participant = cleaned_data.get("participant")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        is_active = cleaned_data.get("is_active")

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be earlier than start date.")

        if participant and is_active and self.coordinator:
            duplicate = ParticipantCoordinatorAssignment.objects.filter(
                participant=participant,
                coordinator=self.coordinator,
                is_active=True,
            )
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error(
                    "participant",
                    "This participant already has an active assignment for this support coordinator.",
                )
        return cleaned_data

    def save(self, commit=True):
        assignment = super().save(commit=False)
        if self.coordinator:
            assignment.coordinator = self.coordinator
        if commit:
            assignment.save()
        return assignment


class CoordinationLogForm(forms.ModelForm):
    HOUR_DECIMAL_PLACES = Decimal("0.01")

    class Meta:
        model = CoordinationLog
        fields = [
            "participant",
            "service_date",
            "start_time",
            "end_time",
            "break_minutes",
            "actual_hours",
            "coordination_type",
            "case_notes",
            "coordinator_notes",
        ]
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "case_notes": forms.Textarea(attrs={"rows": 5}),
            "coordinator_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        coordinator = kwargs.pop("coordinator", None)
        super().__init__(*args, **kwargs)
        self.fields["participant"].queryset = assigned_participants_for(
            coordinator,
        ).order_by("last_name", "first_name")

    def clean(self):
        cleaned_data = super().clean()
        service_date = cleaned_data.get("service_date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        break_minutes = cleaned_data.get("break_minutes")
        actual_hours = cleaned_data.get("actual_hours")

        duration_minutes = None
        if service_date and start_time and end_time:
            starts_at = datetime.combine(service_date, start_time)
            ends_at = datetime.combine(service_date, end_time)
            duration_minutes = int((ends_at - starts_at).total_seconds() // 60)
            if duration_minutes <= 0:
                self.add_error("end_time", "End time must be after start time.")
                duration_minutes = None

        break_is_valid = True
        if duration_minutes is not None and break_minutes is not None:
            if break_minutes >= duration_minutes:
                self.add_error(
                    "break_minutes",
                    "Break minutes must be less than the total duration.",
                )
                break_is_valid = False

        if actual_hours is not None and actual_hours <= 0:
            self.add_error("actual_hours", "Actual hours must be greater than zero.")

        if (
            duration_minutes is not None
            and break_minutes is not None
            and break_is_valid
            and actual_hours is not None
            and actual_hours > 0
        ):
            worked_minutes = duration_minutes - break_minutes
            expected_hours = (Decimal(worked_minutes) / Decimal("60")).quantize(
                self.HOUR_DECIMAL_PLACES,
                rounding=ROUND_HALF_UP,
            )
            if actual_hours != expected_hours:
                self.add_error(
                    "actual_hours",
                    "Actual hours must match the time worked after breaks.",
                )

        return cleaned_data
