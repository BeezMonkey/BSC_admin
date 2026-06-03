# Phase 42: Roster Expanded Keyword Filters Plan

## Steps

1. Add focused Roster tests for participant NDIS/phone searches and worker email/phone searches.
2. Confirm those tests fail against the existing name-only filters.
3. Extend the Roster queryset filters in `scheduling/views.py`.
4. Update Roster filter placeholders in `templates/scheduling/roster_list.html`.
5. Run focused tests, scheduling tests, Django check, and the full test suite.

## Verification

- `python manage.py test scheduling.tests_shifts.ShiftSchedulingTests.test_roster_can_filter_participant_by_ndis_or_phone scheduling.tests_shifts.ShiftSchedulingTests.test_roster_can_filter_worker_by_email_or_phone`
- `python manage.py test scheduling`
- `python manage.py check`
- `python manage.py test`
