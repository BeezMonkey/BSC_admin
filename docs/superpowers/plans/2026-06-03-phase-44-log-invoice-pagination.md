# Phase 44: Service Log and Invoice Pagination Plan

## Steps

1. Add failing tests for Service Log pagination and Invoice pagination.
2. Confirm both lists currently return unpaginated querysets.
3. Apply the shared pagination helper to Service Log and Invoice list views.
4. Include the shared pagination template on both list pages.
5. Run focused tests, module tests, Django check, and the full test suite.

## Verification

- `python manage.py test service_logs.tests_review.ServiceLogReviewTests.test_service_log_list_is_paginated_and_preserves_filters invoices.tests_invoices.InvoiceGenerationTests.test_invoice_list_is_paginated_and_preserves_filters`
- `python manage.py test service_logs invoices`
- `python manage.py check`
- `python manage.py test`
