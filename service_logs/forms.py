from decimal import Decimal

from django import forms

from participants.models import Participant
from scheduling.models import Shift, SupportItem

from .models import ServiceLog


class ServiceLogForm(forms.ModelForm):
    class Meta:
        model = ServiceLog
        fields = [
            "actual_start_time",
            "actual_end_time",
            "break_minutes",
            "kilometres",
            "case_notes",
            "worker_notes",
        ]
        widgets = {
            "actual_start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "actual_end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "case_notes": forms.Textarea(attrs={"rows": 5}),
            "worker_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("actual_start_time")
        end_time = cleaned_data.get("actual_end_time")
        break_minutes = cleaned_data.get("break_minutes") or 0

        if start_time and end_time and end_time <= start_time:
            self.add_error(
                "actual_end_time",
                "Actual end time must be after actual start time.",
            )
            return cleaned_data

        if start_time and end_time:
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            total_minutes = end_minutes - start_minutes - break_minutes
            if total_minutes <= 0:
                self.add_error("break_minutes", "Actual hours must be greater than 0.")
            else:
                cleaned_data["actual_hours"] = (
                    Decimal(total_minutes) / Decimal(60)
                ).quantize(Decimal("0.01"))

        return cleaned_data


class UnscheduledServiceLogForm(ServiceLogForm):
    service_type = forms.ChoiceField(choices=Shift.ServiceType.choices)

    class Meta(ServiceLogForm.Meta):
        fields = [
            "participant",
            "service_date",
            "support_item",
            "service_type",
            "actual_start_time",
            "actual_end_time",
            "break_minutes",
            "kilometres",
            "case_notes",
            "worker_notes",
            "unscheduled_reason",
        ]
        widgets = {
            **ServiceLogForm.Meta.widgets,
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "case_notes": forms.Textarea(attrs={"rows": 5}),
            "worker_notes": forms.Textarea(attrs={"rows": 3}),
            "unscheduled_reason": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, worker=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participant"].queryset = Participant.objects.none()
        if worker:
            self.fields["participant"].queryset = (
                Participant.objects.filter(
                    status=Participant.Status.ACTIVE,
                    worker_assignments__worker=worker,
                    worker_assignments__is_active=True,
                )
                .distinct()
                .order_by("last_name", "first_name")
            )
        self.fields["support_item"].queryset = SupportItem.active_items()
        self.fields["participant"].empty_label = "Select participant"
        self.fields["support_item"].empty_label = "Select support item"

    def clean_unscheduled_reason(self):
        reason = self.cleaned_data.get("unscheduled_reason", "").strip()
        if not reason:
            raise forms.ValidationError("Unscheduled reason is required.")
        return reason
