from django import forms


class SupportItemSelect(forms.Select):
    def __init__(self, attrs=None, choices=()):
        attrs = {
            **(attrs or {}),
            "data-support-item-picker": "",
        }
        super().__init__(attrs=attrs, choices=choices)

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-category"] = (
                instance.category or "Other support items"
            )
        return option
