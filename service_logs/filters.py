from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from django.utils.dateparse import parse_date


DATE_RANGE_CHOICES = (
    ("all", "All dates"),
    ("this_week", "This week"),
    ("last_week", "Last week"),
    ("this_fortnight", "This fortnight"),
    ("last_fortnight", "Last fortnight"),
    ("this_month", "This month"),
    ("last_month", "Last month"),
    ("custom", "Custom"),
)


def _safe_parse_date(value):
    try:
        return parse_date(value) if value else None
    except ValueError:
        return None


def resolve_service_date_filter(key, start_value, end_value, *, today):
    valid_keys = {value for value, _label in DATE_RANGE_CHOICES}
    key = key if key in valid_keys else "all"
    monday = today - timedelta(days=today.weekday())
    ranges = {
        "this_week": (monday, monday + timedelta(days=6)),
        "last_week": (
            monday - timedelta(days=7),
            monday - timedelta(days=1),
        ),
        "this_fortnight": (monday, monday + timedelta(days=13)),
        "last_fortnight": (
            monday - timedelta(days=14),
            monday - timedelta(days=1),
        ),
        "this_month": (
            today.replace(day=1),
            today.replace(day=monthrange(today.year, today.month)[1]),
        ),
    }
    previous_month_last = today.replace(day=1) - timedelta(days=1)
    ranges["last_month"] = (
        previous_month_last.replace(day=1),
        previous_month_last,
    )

    if key == "custom":
        return {
            "key": key,
            "start": _safe_parse_date(start_value),
            "end": _safe_parse_date(end_value),
            "start_value": start_value,
            "end_value": end_value,
        }

    start, end = ranges.get(key, (None, None))
    return {
        "key": key,
        "start": start,
        "end": end,
        "start_value": start.isoformat() if start else "",
        "end_value": end.isoformat() if end else "",
    }


def format_hours(value):
    value = value or Decimal("0")
    return format(value.normalize(), "f")
