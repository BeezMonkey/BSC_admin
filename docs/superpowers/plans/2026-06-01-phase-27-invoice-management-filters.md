# Phase 27 Invoice Management Filters Plan

## Steps

1. Add failing tests for invoice list filters, draft deletion, issued delete blocking, and service log release on cancel.
2. Implement invoice list filtering with preserved form values.
3. Add draft invoice delete route, view, UI action, and audit action.
4. Release service logs when deleting draft invoices or cancelling draft/issued invoices.
5. Document V1 invoice correction rules.
6. Run invoice tests, full Django tests, and system checks.

## Acceptance

- Finance/admin can narrow invoices by number, participant, status, and period.
- Draft invoices can be deleted.
- Issued invoices cannot be deleted.
- Draft/issued cancellation releases service logs for replacement invoicing.
- Existing invoice export and status transition tests remain green.
