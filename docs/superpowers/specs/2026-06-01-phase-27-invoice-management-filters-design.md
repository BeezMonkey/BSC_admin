# Phase 27 Invoice Management Filters Design

## Goal

Improve the finance/admin invoice management workflow before broader trial use.

## Scope

- Add invoice list filters for invoice number, participant, status, and period date range.
- Allow draft invoice deletion.
- Ensure draft deletion releases related service logs for re-invoicing.
- Ensure draft/issued invoice cancellation releases related service logs for re-invoicing.
- Keep paid invoices locked from delete/cancel correction actions.

## Non-goals

- No line-level invoice editing.
- No credit note workflow.
- No paid invoice voiding.
- No bulk invoice generation changes.
- No major visual redesign.

## Behaviour Notes

Invoice period filters should find invoices whose invoice period overlaps the selected range, not only invoices fully contained inside it.

Cancellation keeps the invoice record as Cancelled but removes its invoice line locks so the underlying service logs can be included in a replacement invoice.
