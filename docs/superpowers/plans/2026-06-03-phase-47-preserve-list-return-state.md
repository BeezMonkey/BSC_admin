# Phase 47: Preserve List Return State Plan

## Steps

1. Add tests for list View links and detail Back links across the five main lists.
2. Confirm the tests fail against current direct detail links.
3. Add a safe return URL helper.
4. Pass current list URLs from list views.
5. Pass safe return URLs from detail views.
6. Update list and detail templates.
7. Run focused tests, module tests, Django check, and the full test suite.

## Verification

- `python manage.py test participants.tests.ParticipantManagementTests.test_participant_detail_back_link_preserves_list_state workers.tests.SupportWorkerManagementTests.test_worker_detail_back_link_preserves_list_state scheduling.tests_shifts.ShiftSchedulingTests.test_shift_detail_back_link_preserves_roster_state service_logs.tests_review.ServiceLogReviewTests.test_service_log_detail_back_link_preserves_list_state invoices.tests_invoices.InvoiceGenerationTests.test_invoice_detail_back_link_preserves_list_state`
- `python manage.py test participants workers scheduling service_logs invoices`
- `python manage.py check`
- `python manage.py test`
