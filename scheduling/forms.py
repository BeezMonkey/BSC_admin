from decimal import Decimal

from django import forms

from .models import Shift, SupportItem


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
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
            "admin_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.created_by = kwargs.pop("created_by", None)
        super().__init__(*args, **kwargs)
        self.fields["support_item"].queryset = SupportItem.active_items()

    def clean(self):
        cleaned_data = super().clean()
        worker = cleaned_data.get("worker")
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

        return cleaned_data

    def save(self, commit=True):
        shift = super().save(commit=False)
        shift.planned_hours = self.cleaned_data["planned_hours"]
        if self.created_by and not shift.created_by_id:
            shift.created_by = self.created_by
        if commit:
            shift.save()
            self.save_m2m()
        return shift
