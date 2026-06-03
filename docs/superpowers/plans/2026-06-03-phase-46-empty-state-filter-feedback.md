# Phase 46: Empty State Filter Feedback Plan

## Steps

1. Add focused tests for filtered empty states on all five high-volume lists.
2. Confirm the tests fail against the current generic empty messages.
3. Pass a `has_filters` flag from each list view.
4. Update each list template to show filter-specific empty state copy and a clear filters action.
5. Run focused tests, module tests, Django check, and the full test suite.

## Verification

- `python manage.py test participants.tests.ParticipantManagementTests.test_participant_list_distinguishes_empty_filter_results workers.tests.SupportWorkerManagementTests.test_worker_list_distinguishes_empty_filter_results scheduling.tests_shifts.ShiftSchedulingTests.test_roster_list_distinguishes_empty_filter_results service_logs.tests_review.ServiceLogReviewTests.test_service_log_list_distinguishes_empty_filter_results invoices.tests_invoices.InvoiceGenerationTests.test_invoice_list_distinguishes_empty_filter_results`
- `python manage.py test participants workers scheduling service_logs invoices`
- `python manage.py check`
- `python manage.py test`
