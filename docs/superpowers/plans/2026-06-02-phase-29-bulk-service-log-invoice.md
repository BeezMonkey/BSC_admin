# Phase 29 Bulk Service Log Invoice Plan

## Steps

1. Add tests for service log bulk selection, selected-log preview, mixed-participant blocking, and selected-only invoice creation.
2. Add selectable rows for Approved service logs.
3. Route selected `service_log_ids` into the existing invoice creation page.
4. Add selected-log validation for Approved, uninvoiced, same-participant logs.
5. Preserve existing date-range invoice creation when no selected logs are provided.
6. Add hidden selected IDs to the invoice confirmation form.
7. Run targeted tests, full Django tests, system check, and browser smoke test.

## Acceptance

- Approved logs can be selected from the Service Logs list.
- Selected logs open Create Invoice with participant and period prefilled.
- Preview and final invoice include only selected logs.
- Mixed-participant or unavailable selections are blocked.
- Existing invoice generation flows continue to pass.
