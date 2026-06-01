# Invoice Management Rules

Phase 27 adds safer invoice review and correction controls for the V1 trial workflow.

## Invoice List Review

Finance/admin users can filter invoices by:

- Invoice number
- Participant name
- Status
- Invoice period overlap with a selected date range

The date filters use overlap logic. For example, a June invoice appears when the selected range touches any day in June.

## Correction Rules

- Draft invoices can be deleted.
- Deleting a draft invoice releases its invoice lines back to Approved service logs.
- Draft and Issued invoices can be cancelled.
- Cancelling an invoice releases its invoice lines back to Approved service logs so they can be invoiced again.
- Paid invoices cannot be cancelled or deleted in V1.

## Current V1 Boundary

The system does not yet support line-level invoice editing, credit notes, voided paid invoices, or claim reconciliation. These should be designed as separate finance-control phases after trial feedback.
