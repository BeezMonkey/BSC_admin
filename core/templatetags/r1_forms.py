from copy import deepcopy

from django import template
from django.forms import ModelChoiceField


register = template.Library()


@register.filter
def choice_hint(bound_field, caption):
    if not isinstance(bound_field.field, ModelChoiceField):
        return bound_field
    # Render a copy so the original form's field, choices and validation stay intact.
    field = deepcopy(bound_field.field)
    field.empty_label = caption
    return field.get_bound_field(bound_field.form, bound_field.name)
