from decimal import Decimal

from django import forms

from participants.models import Participant

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

    def __init__(self, *args, service_log, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_log = service_log

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if not amount:
            return Decimal("0.00")
        if self.service_log.kilometres <= Decimal("0.00"):
            raise forms.ValidationError(
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
