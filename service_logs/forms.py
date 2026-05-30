from decimal import Decimal

from django import forms

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
