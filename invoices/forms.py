from decimal import Decimal

from django import forms

from participants.models import Participant
from scheduling.models import SupportItem
from scheduling.widgets import SupportItemSelect
from service_logs.forms import ServiceLogForm

from .models import InvoiceSettings


class InvoiceCreateForm(forms.Form):
    participant = forms.ModelChoiceField(
        empty_label="Select participant",
        queryset=Participant.objects.all(),
    )
    period_start = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "dd/mm/yyyy"})
    )
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "dd/mm/yyyy"})
    )

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        if period_start and period_end and period_end < period_start:
            self.add_error("period_end", "Period end must be on or after period start.")
        return cleaned_data


class SupportCoordinationInvoiceCreateForm(forms.Form):
    participant = forms.ModelChoiceField(
        empty_label="Select participant",
        queryset=Participant.objects.all(),
    )
    period_start = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "dd/mm/yyyy"})
    )
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "dd/mm/yyyy"})
    )
    support_item = forms.ModelChoiceField(
        empty_label="Select support item",
        queryset=SupportItem.objects.filter(is_active=True).order_by("item_number"),
    )

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        if period_start and period_end and period_end < period_start:
            self.add_error("period_end", "Period end must be on or after period start.")
        return cleaned_data


class BillingSupportItemSelect(SupportItemSelect):
    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        instance = getattr(option["value"], "instance", None)
        if instance is not None:
            option["attrs"]["data-price"] = str(instance.price_limit)
            option["attrs"]["data-item-name"] = instance.name
            option["attrs"]["data-item-code"] = instance.item_number
        return option


class BillingAdjustmentForm(forms.Form):
    correct_time = forms.BooleanField(label="Correct service time", required=False)
    actual_start_time = forms.TimeField(label="Actual start", required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    actual_end_time = forms.TimeField(label="Actual end", required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    break_minutes = forms.IntegerField(label="Break (min)", required=False, min_value=0)
    source_version = forms.CharField(required=False, widget=forms.HiddenInput())
    support_item = forms.ModelChoiceField(
        label="Billing support item", required=False,
        empty_label="Keep original item", queryset=SupportItem.objects.none(),
        widget=BillingSupportItemSelect(),
    )
    kilometres = forms.DecimalField(
        label="Confirmed kilometres", required=False, min_value=Decimal("0.00"),
        max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "Optional"}),
    )
    reason = forms.ChoiceField(required=False, choices=[
        ("", "Select a reason"), ("service_changed", "Actual service changed"),
        ("missing_km", "Kilometres omitted from log"),
        ("corrected_km", "Kilometres corrected after checking"), ("other", "Other"),
        ("incorrect_time", "Incorrect service time"), ("multiple", "Multiple corrections"),
    ])
    reason_details = forms.CharField(
        label="Reason details", required=False, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, service_log, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_log = service_log
        self.fields["support_item"].queryset = SupportItem.objects.filter(
            is_active=True, unit=SupportItem.Unit.HOUR,
        ).order_by("item_number")
        self.initial.setdefault("kilometres", service_log.kilometres or "")
        for name in ("actual_start_time", "actual_end_time", "break_minutes"):
            self.initial.setdefault(name, getattr(service_log, name))
        self.initial.setdefault("source_version", service_log.updated_at.isoformat())
        self.effective_item = service_log.support_item
        self.effective_kilometres = service_log.kilometres
        self.effective_hours = service_log.actual_hours
        self.time_changed = False
        self.corrected_time = {}
        self.is_adjusted = False
        self.reason_text = ""

    def clean(self):
        data = super().clean()
        if data.get("source_version") and data["source_version"] != self.service_log.updated_at.isoformat():
            self.add_error(None, "This log changed since the preview. Reload before applying adjustments.")
        if data.get("correct_time"):
            if not data.get("source_version"):
                self.add_error(None, "Reload this log before correcting service time.")
            names = ("actual_start_time", "actual_end_time", "break_minutes")
            for name in names:
                if data.get(name) is None and name not in self.errors:
                    self.add_error(name, "This field is required when correcting service time.")
            if all(data.get(name) is not None for name in names):
                time_form = ServiceLogForm(data={
                    **{name: data[name] for name in names},
                    "kilometres": self.service_log.kilometres,
                    "case_notes": self.service_log.case_notes,
                })
                if time_form.is_valid():
                    self.time_changed = any(data[name] != getattr(self.service_log, name) for name in names)
                    if self.time_changed:
                        self.corrected_time = {name: data[name] for name in names}
                        self.effective_hours = time_form.cleaned_data["actual_hours"]
                else:
                    for name, errors in time_form.errors.items():
                        self.add_error(name if name in names else None, errors)
        self.effective_item = data.get("support_item") or self.service_log.support_item
        km = data.get("kilometres")
        self.effective_kilometres = self.service_log.kilometres if km is None else km
        self.is_adjusted = (
            self.effective_item.pk != self.service_log.support_item_id
            or self.effective_kilometres != self.service_log.kilometres
            or self.time_changed
        )
        if self.is_adjusted:
            reason = data.get("reason")
            if not reason:
                self.add_error("reason", "Select a reason for this billing adjustment.")
            elif reason == "other" and not data.get("reason_details"):
                self.add_error("reason_details", "Enter a reason for this billing adjustment.")
            else:
                self.reason_text = dict(self.fields["reason"].choices).get(reason, "")
                if reason == "other":
                    self.reason_text += ": " + data["reason_details"]
        return data


class TravelClaimForm(forms.Form):
    amount = forms.DecimalField(
        label="Travel claim amount",
        required=False,
        min_value=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "min": "0",
                "step": "0.01",
                "placeholder": "0.00",
            }
        ),
    )

    def __init__(self, *args, service_log, confirmed_kilometres=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_log = service_log
        self.uses_confirmed_kilometres = confirmed_kilometres is not None
        self.confirmed_kilometres = (
            service_log.kilometres if confirmed_kilometres is None else confirmed_kilometres
        )

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if not amount:
            return Decimal("0.00")
        if self.confirmed_kilometres <= Decimal("0.00"):
            raise forms.ValidationError(
                "Enter confirmed kilometres before adding a travel claim."
                if self.uses_confirmed_kilometres else
                "Worker must record kilometres before a travel claim can be added."
            )
        return amount


class InvoiceSettingsForm(forms.ModelForm):
    remove_logo = forms.BooleanField(required=False)

    class Meta:
        model = InvoiceSettings
        fields = [
            "business_name",
            "abn",
            "phone",
            "email",
            "address",
            "bank_name",
            "account_name",
            "bsb",
            "account_number",
            "invoice_prefix",
            "next_invoice_sequence",
            "accent_colour",
            "logo",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "accent_colour": forms.TextInput(attrs={"placeholder": "#6f2c80"}),
            "logo": forms.FileInput(),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("remove_logo"):
            instance.logo = ""
        if commit:
            instance.save()
        return instance
