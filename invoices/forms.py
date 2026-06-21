from django import forms

from participants.models import Participant

from .models import InvoiceSettings


class InvoiceCreateForm(forms.Form):
    participant = forms.ModelChoiceField(queryset=Participant.objects.all())
    period_start = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    period_end = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        if period_start and period_end and period_end < period_start:
            self.add_error("period_end", "Period end must be on or after period start.")
        return cleaned_data


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
