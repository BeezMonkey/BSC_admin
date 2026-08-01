from django import template

from core.formatting import format_display_time


register = template.Library()


@register.filter
def display_time(value):
    return format_display_time(value)
