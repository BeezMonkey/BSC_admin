from django import forms


SUPPORT_ITEM_PICKER_GROUPS = (
    (("assistance with self-care activities",), "Self-care"),
    (
        ("access community social and rec", "community access"),
        "Community access",
    ),
    (("provider travel",), "Provider travel"),
    (("support coordination",), "Support coordination"),
)


def support_item_picker_group(instance):
    searchable_text = f"{instance.name} {instance.category}".casefold()
    for keywords, group_label in SUPPORT_ITEM_PICKER_GROUPS:
        if any(keyword in searchable_text for keyword in keywords):
            return group_label
    if instance.category.casefold() == "core supports":
        return "Other core supports"
    return instance.category or "Other support items"


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
            option["attrs"]["data-category"] = support_item_picker_group(instance)
        return option
