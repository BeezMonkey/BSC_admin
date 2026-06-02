# Phase 34 Admin Dashboard Summary Design

## Goal

Add a compact operations summary to the admin dashboard so office users can see common follow-up work immediately after login.

## Scope

- Show counts for draft shifts, submitted service logs, approved un-invoiced logs, draft invoices, and issued invoices.
- Link each count to the existing filtered list page.
- Keep existing roster, service log, invoice, and module navigation behavior unchanged.

## Summary Mapping

- Draft shifts link to the roster filtered by draft status.
- Submitted service logs link to the service log review list.
- Approved service logs count only logs that are not attached to an invoice line.
- Draft invoices link to invoices filtered by draft status.
- Issued invoices link to invoices filtered by issued status.

## Out Of Scope

- New workflow states.
- New dashboard charts.
- Automatic notifications or reminders.
- Changes to invoice creation or service log approval behavior.
