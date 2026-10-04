"""Bundled holiday reminders, not scheduling or billing rules."""

import json
from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path


REGIONS = ("QLD", "Brisbane", "Logan", "Gold Coast")
CALENDAR_PATH = Path(__file__).parent / "data" / "qld_public_holidays.json"


@lru_cache(maxsize=1)
def _load_calendar():
    return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return None
        if parsed.isoformat() == value:
            return parsed
    return None


def calendar_data() -> dict:
    """Return the verified calendar without exposing the shared cached data."""
    return deepcopy(_load_calendar())


def holidays_on(value) -> list:
    """Return known reminders; an empty list does not establish coverage."""
    day = _as_date(value)
    if day is None:
        return []
    return deepcopy(_load_calendar()["holidays"].get(day.isoformat(), []))


def coverage_warning(start, end=None) -> str:
    """List unverified regions for every year touched by an inclusive range."""
    start_date = _as_date(start)
    end_date = start_date if end is None else _as_date(end)
    if start_date is None or end_date is None:
        return ""

    first_year, last_year = sorted((start_date.year, end_date.year))
    coverage = _load_calendar()["coverage"]
    gaps = []
    for year in range(first_year, last_year + 1):
        verified_regions = coverage.get(str(year), [])
        missing_regions = [region for region in REGIONS if region not in verified_regions]
        if missing_regions:
            gaps.append(f"{year}: {', '.join(missing_regions)}")

    if not gaps:
        return ""
    return (
        f"Holiday dates are not verified for {'; '.join(gaps)}. "
        "Check official Queensland holiday dates; do not assume there are no holidays."
    )
