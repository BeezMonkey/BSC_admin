# Phase 45: List Sorting Basics Plan

## Steps

1. Add focused tests for sorting on all five high-volume lists.
2. Confirm the tests fail against the current table headers and default ordering.
3. Add a shared safe sorting helper.
4. Apply whitelisted sorting to each list view.
5. Add sortable table header links and lightweight styling.
6. Run focused tests, module tests, Django check, and the full test suite.

## Verification

- `python manage.py test participants.tests.ParticipantManagementTests.test_participant_list_can_sort_by_name_and_preserve_filters workers.tests.SupportWorkerManagementTests.test_worker_list_can_sort_by_status_and_preserve_filters scheduling.tests_shifts.ShiftSchedulingTests.test_roster_list_can_sort_by_date_and_preserve_filters service_logs.tests_review.ServiceLogReviewTests.test_service_log_list_can_sort_by_date_and_preserve_filters invoices.tests_invoices.InvoiceGenerationTests.test_invoice_list_can_sort_by_total_and_preserve_filters`
- `python manage.py test participants workers scheduling service_logs invoices`
- `python manage.py check`
- `python manage.py test`
