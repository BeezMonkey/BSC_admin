from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import UserProfile

from .models import SupportWorker


class SupportWorkerCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)
    account_active = forms.BooleanField(required=False, initial=True)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=30, required=False)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    employment_type = forms.ChoiceField(choices=SupportWorker.EmploymentType.choices)
    abn = forms.CharField(max_length=20, required=False)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    status = forms.ChoiceField(choices=SupportWorker.Status.choices)
    police_check_status = forms.ChoiceField(choices=SupportWorker.ComplianceStatus.choices)
    police_check_expiry = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    wwcc_status = forms.ChoiceField(
        label="WWCC / Blue Card status",
        choices=SupportWorker.ComplianceStatus.choices,
    )
    wwcc_expiry = forms.DateField(
        label="WWCC / Blue Card expiry",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if get_user_model().objects.filter(email=email).exists() or SupportWorker.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
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
            role=UserProfile.Role.SUPPORT_WORKER,
            phone=data["phone"],
            is_active_worker=data["status"] == SupportWorker.Status.ACTIVE,
        )
        return SupportWorker.objects.create(
            user=user,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            address=data["address"],
            employment_type=data["employment_type"],
            abn=data["abn"],
            start_date=data["start_date"],
            status=data["status"],
            police_check_status=data["police_check_status"],
            police_check_expiry=data["police_check_expiry"],
            wwcc_status=data["wwcc_status"],
            wwcc_expiry=data["wwcc_expiry"],
            notes=data["notes"],
        )


class SupportWorkerEditForm(forms.ModelForm):
    account_active = forms.BooleanField(required=False)

    class Meta:
        model = SupportWorker
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "address",
            "employment_type",
            "abn",
            "start_date",
            "status",
            "police_check_status",
            "police_check_expiry",
            "wwcc_status",
            "wwcc_expiry",
            "notes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "police_check_expiry": forms.DateInput(attrs={"type": "date"}),
            "wwcc_expiry": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["account_active"].initial = self.instance.user.is_active

    def clean_email(self):
        email = self.cleaned_data["email"]
        duplicate_user = get_user_model().objects.filter(email=email).exclude(
            pk=self.instance.user_id
        )
        duplicate_worker = SupportWorker.objects.filter(email=email).exclude(
            pk=self.instance.pk
        )
        if duplicate_user.exists() or duplicate_worker.exists():
            raise forms.ValidationError("Email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        worker = super().save(commit=False)
        worker.user.email = self.cleaned_data["email"]
        worker.user.first_name = self.cleaned_data["first_name"]
        worker.user.last_name = self.cleaned_data["last_name"]
        worker.user.is_active = self.cleaned_data["account_active"]
        if commit:
            worker.user.save()
            worker.save()
            profile, _ = UserProfile.objects.get_or_create(
                user=worker.user,
                defaults={"role": UserProfile.Role.SUPPORT_WORKER},
            )
            profile.role = UserProfile.Role.SUPPORT_WORKER
            profile.phone = worker.phone
            profile.is_active_worker = worker.status == SupportWorker.Status.ACTIVE
            profile.save()
        return worker
