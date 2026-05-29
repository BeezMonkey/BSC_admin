from django import forms

from .models import SupportItem


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
