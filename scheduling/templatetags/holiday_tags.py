from django import template

from scheduling.holidays import calendar_data, coverage_warning
from scheduling.holidays import holidays_on as get_holidays


register = template.Library()


@register.simple_tag
def holiday_calendar_data():
    return calendar_data()


@register.simple_tag
def holidays_on(value):
    return get_holidays(value)


@register.simple_tag
def holiday_coverage_warning(start, end=None):
    return coverage_warning(start, end)
