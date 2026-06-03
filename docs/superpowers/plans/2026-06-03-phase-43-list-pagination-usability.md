# Phase 43: List Pagination Usability Plan

## Steps

1. Add tests for Participants, Support Workers, and Roster pagination.
2. Confirm the tests fail against unpaginated querysets.
3. Add a shared pagination helper.
4. Add a shared pagination template and CSS.
5. Connect Participants, Support Workers, and Roster views to the helper.
6. Run focused tests, module tests, Django check, and the full test suite.

## Verification

- `python manage.py test participants.tests.ParticipantManagementTests.test_participant_list_is_paginated_and_preserves_filters workers.tests.SupportWorkerManagementTests.test_worker_list_is_paginated_and_preserves_filters scheduling.tests_shifts.ShiftSchedulingTests.test_roster_list_is_paginated_and_preserves_filters`
- `python manage.py test participants workers scheduling`
- `python manage.py check`
- `python manage.py test`
