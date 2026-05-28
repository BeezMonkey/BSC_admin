from django import forms

from .models import Participant


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = [
            "first_name",
            "last_name",
            "preferred_name",
            "date_of_birth",
            "ndis_number",
            "status",
            "phone",
            "email",
            "address_line_1",
            "address_line_2",
            "suburb",
            "state",
            "postcode",
            "emergency_contact_name",
            "emergency_contact_relationship",
            "emergency_contact_phone",
            "emergency_contact_email",
            "plan_start_date",
            "plan_end_date",
            "management_type",
            "plan_manager_name",
            "plan_manager_email",
            "plan_manager_phone",
            "support_coordinator_name",
            "support_coordinator_email",
            "support_coordinator_phone",
            "worker_visible_notes",
            "address_access_instructions",
            "risk_safety_notes",
            "internal_notes",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "plan_start_date": forms.DateInput(attrs={"type": "date"}),
            "plan_end_date": forms.DateInput(attrs={"type": "date"}),
            "worker_visible_notes": forms.Textarea(attrs={"rows": 3}),
            "address_access_instructions": forms.Textarea(attrs={"rows": 3}),
            "risk_safety_notes": forms.Textarea(attrs={"rows": 3}),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_postcode(self):
        postcode = self.cleaned_data.get("postcode", "")
        if postcode and (len(postcode) != 4 or not postcode.isdigit()):
            raise forms.ValidationError("Enter a 4-digit Australian postcode.")
        return postcode

    def clean_ndis_number(self):
        ndis_number = self.cleaned_data.get("ndis_number")
        if not ndis_number:
            return None

        duplicate = Participant.objects.filter(ndis_number=ndis_number)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError(
                "Participant with this NDIS number already exists."
            )
        return ndis_number

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("plan_start_date")
        end_date = cleaned_data.get("plan_end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error(
                "plan_end_date",
                "Plan end date cannot be earlier than plan start date.",
            )
        return cleaned_data
