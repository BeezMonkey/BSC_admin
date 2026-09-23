from decimal import Decimal

from django import forms
from django.db.models import Q

from core.formatting import format_display_time

from .models import PlannedMultiWorkerSupport, Shift, SupportItem
from .widgets import SupportItemSelect
from workers.models import SupportWorker


def schedulable_worker_queryset(include_worker=None):
    filters = Q(status=SupportWorker.Status.ACTIVE)
    if include_worker and include_worker.pk:
        filters |= Q(pk=include_worker.pk)
    return SupportWorker.objects.filter(filters).order_by("last_name", "first_name")


class SupportItemForm(forms.ModelForm):
    class Meta:
        model = SupportItem
        fields = [
            "item_number",
            "name",
            "category",
            "unit",
            "price_limit",
            "gst_code",
            "is_active",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_item_number(self):
        item_number = self.cleaned_data["item_number"]
        duplicate = SupportItem.objects.filter(item_number=item_number)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError(
                "Support item with this item number already exists."
            )
        return item_number

    def clean_price_limit(self):
        price_limit = self.cleaned_data["price_limit"]
        if price_limit < 0:
            raise forms.ValidationError("Price limit cannot be negative.")
        return price_limit


class ShiftForm(forms.ModelForm):
    allow_participant_overlap = forms.BooleanField(required=False)
    multi_worker_reason = forms.ChoiceField(
        choices=PlannedMultiWorkerSupport.Reason.choices,
        required=False,
    )
    multi_worker_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    class Meta:
        model = Shift
        fields = [
            "participant",
            "worker",
            "service_date",
            "start_time",
            "end_time",
            "break_minutes",
            "support_item",
            "service_type",
            "location",
            "address",
            "instructions",
            "admin_notes",
            "status",
        ]
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date", "lang": "en-AU"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "lang": "en-AU"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "lang": "en-AU"}),
            "support_item": SupportItemSelect(),
            "address": forms.Textarea(attrs={"rows": 3}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
            "admin_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.created_by = kwargs.pop("created_by", None)
        self.participant_overlap_shift = None
        self.participant_overlap_shifts = []
        self.participant_overlap_count = 0
        super().__init__(*args, **kwargs)
        self.original_schedule = None
        if self.instance.pk:
            self.original_schedule = {
                "participant_id": self.instance.participant_id,
                "worker_id": self.instance.worker_id,
                "service_date": self.instance.service_date,
                "start_time": self.instance.start_time,
                "end_time": self.instance.end_time,
            }
        self.fields["support_item"].queryset = SupportItem.active_items()
        self.fields["worker"].queryset = schedulable_worker_queryset(
            getattr(self.instance, "worker", None)
        )
        self.fields["participant"].empty_label = "Select participant"
        self.fields["worker"].empty_label = "Select worker"
        self.fields["support_item"].empty_label = "Select support item"
        self.fields["service_type"].choices = self.with_empty_choice_label(
            self.fields["service_type"].choices,
            "Select service type",
        )

    @staticmethod
    def with_empty_choice_label(choices, label):
        choices = list(choices)
        if choices and choices[0][0] == "":
            choices[0] = ("", label)
        return choices

    def clean(self):
        cleaned_data = super().clean()
        participant = cleaned_data.get("participant")
        worker = cleaned_data.get("worker")
        status = cleaned_data.get("status")
        service_date = cleaned_data.get("service_date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        break_minutes = cleaned_data.get("break_minutes") or 0

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")
            return cleaned_data

        if start_time and end_time:
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            total_minutes = end_minutes - start_minutes - break_minutes
            if total_minutes <= 0:
                self.add_error("break_minutes", "Planned hours must be greater than 0.")
            else:
                cleaned_data["planned_hours"] = (
                    Decimal(total_minutes) / Decimal(60)
                ).quantize(Decimal("0.01"))

        if worker and service_date and start_time and end_time:
            overlap = Shift.objects.filter(
                worker=worker,
                service_date=service_date,
                status__in=Shift.ACTIVE_CONFLICT_STATUSES,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if self.instance.pk:
                overlap = overlap.exclude(pk=self.instance.pk)
            if overlap.exists():
                self.add_error("worker", "Worker has an overlapping active shift.")

        if (
            participant
            and worker
            and status in Shift.ACTIVE_CONFLICT_STATUSES
            and service_date
            and start_time
            and end_time
        ):
            participant_overlap = Shift.objects.filter(
                participant=participant,
                service_date=service_date,
                status__in=Shift.ACTIVE_CONFLICT_STATUSES,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exclude(worker=worker)
            if self.instance.pk:
                participant_overlap = participant_overlap.exclude(pk=self.instance.pk)
                if not self.schedule_changed(cleaned_data):
                    approved_support_ids = PlannedMultiWorkerSupport.objects.filter(
                        shifts=self.instance
                    ).values_list("id", flat=True)
                    participant_overlap = participant_overlap.exclude(
                        planned_multi_worker_supports__id__in=approved_support_ids
                    )
            participant_overlap = participant_overlap.order_by(
                "start_time",
                "end_time",
                "id",
            )
            self.participant_overlap_count = participant_overlap.count()
            self.participant_overlap_shift = participant_overlap.first()
            self.participant_overlap_shifts = list(participant_overlap)
            if (
                self.participant_overlap_shift
                and not cleaned_data.get("allow_participant_overlap")
            ):
                self.add_error(
                    "allow_participant_overlap",
                    "Participant has an overlapping active shift. Confirm this is intentional.",
                )
            elif self.participant_overlap_shift and not cleaned_data.get(
                "multi_worker_reason"
            ):
                self.add_error(
                    "multi_worker_reason",
                    "Select why this participant needs multi-worker support.",
                )

        return cleaned_data

    def schedule_changed(self, cleaned_data=None):
        if not self.original_schedule:
            return False
        cleaned_data = cleaned_data or self.cleaned_data
        participant = cleaned_data.get("participant")
        worker = cleaned_data.get("worker")
        current_schedule = {
            "participant_id": participant.id if participant else None,
            "worker_id": worker.id if worker else None,
            "service_date": cleaned_data.get("service_date"),
            "start_time": cleaned_data.get("start_time"),
            "end_time": cleaned_data.get("end_time"),
        }
        return current_schedule != self.original_schedule

    def save(self, commit=True):
        shift = super().save(commit=False)
        shift.planned_hours = self.cleaned_data["planned_hours"]
        if self.created_by and not shift.created_by_id:
            shift.created_by = self.created_by
        if commit:
            shift.save()
            self.save_m2m()
        return shift


class MultiWorkerShiftChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, shift):
        return (
            f"{shift.worker.display_name} - "
            f"{format_display_time(shift.start_time)} to "
            f"{format_display_time(shift.end_time)}"
        )


class PlannedMultiWorkerSupportReviewForm(forms.Form):
    shifts = MultiWorkerShiftChoiceField(
        queryset=Shift.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    reason = forms.ChoiceField(choices=PlannedMultiWorkerSupport.Reason.choices)
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, candidate_shifts, initial_shifts=None, **kwargs):
        super().__init__(*args, **kwargs)
        candidate_ids = [shift.id for shift in candidate_shifts]
        self.fields["shifts"].queryset = Shift.objects.filter(id__in=candidate_ids).select_related(
            "participant",
            "worker",
        )
        if initial_shifts and not self.is_bound:
            self.initial["shifts"] = [shift.id for shift in initial_shifts]

    def clean_shifts(self):
        shifts = list(self.cleaned_data["shifts"])
        if len(shifts) < 2:
            raise forms.ValidationError("Select at least two overlapping shifts.")
        if len({shift.participant_id for shift in shifts}) != 1:
            raise forms.ValidationError("Selected shifts must have the same participant.")
        if len({shift.service_date for shift in shifts}) != 1:
            raise forms.ValidationError("Selected shifts must be on the same date.")
        if len({shift.worker_id for shift in shifts}) != len(shifts):
            raise forms.ValidationError("Each selected shift must have a different worker.")
        overlap_start = max(shift.start_time for shift in shifts)
        overlap_end = min(shift.end_time for shift in shifts)
        if overlap_start >= overlap_end:
            raise forms.ValidationError("Selected shifts must share an overlapping time window.")
        return shifts


class RecurringShiftForm(forms.Form):
    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_FORTNIGHTLY = "fortnightly"
    FREQUENCY_CHOICES = (
        (FREQUENCY_WEEKLY, "Weekly"),
        (FREQUENCY_FORTNIGHTLY, "Fortnightly"),
    )

    participant = forms.ModelChoiceField(queryset=None)
    worker = forms.ModelChoiceField(queryset=None)
    frequency = forms.ChoiceField(choices=FREQUENCY_CHOICES)
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    break_minutes = forms.IntegerField(min_value=0, initial=0)
    support_item = forms.ModelChoiceField(
        queryset=SupportItem.active_items(),
        widget=SupportItemSelect(),
    )
    service_type = forms.ChoiceField(choices=Shift.ServiceType.choices)
    location = forms.CharField(required=False, max_length=150)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    instructions = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    admin_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from participants.models import Participant

        self.fields["participant"].queryset = Participant.objects.all()
        self.fields["worker"].queryset = schedulable_worker_queryset()
        self.fields["support_item"].queryset = SupportItem.active_items()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        break_minutes = cleaned_data.get("break_minutes") or 0

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date must be on or after start date.")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")
            return cleaned_data

        if start_time and end_time:
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            total_minutes = end_minutes - start_minutes - break_minutes
            if total_minutes <= 0:
                self.add_error("break_minutes", "Planned hours must be greater than 0.")
            else:
                cleaned_data["planned_hours"] = (
                    Decimal(total_minutes) / Decimal(60)
                ).quantize(Decimal("0.01"))

        return cleaned_data
