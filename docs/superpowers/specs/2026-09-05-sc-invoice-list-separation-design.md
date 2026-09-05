# SC Invoice List Separation Design

## Goal

Separate Support Coordination invoices into their own Admin management page so contractor billing is easier to review, filter, and reconcile, without changing the existing invoice data model or billing rules.

## Scope

This change is a management UI separation only.

In scope:
- Keep existing `Invoice` and `InvoiceLine` models.
- Keep existing SC invoice creation, detail, PDF, CSV, status, cancel, and delete behavior.
- Add a dedicated Admin list page for invoices where `invoice_type = support_coordination`.
- Change the existing `Invoices` list page to show service invoices only.
- Add `SC Invoices` to the Admin sidebar under the `Coordination` section.
- Keep Admin/super-admin access to both invoice lists.
- Keep accountant access limited to service invoices only.

Out of scope:
- No SC portal invoice access.
- No invoice model split.
- No invoice number rule change.
- No PDF/CSV layout redesign.
- No changes to Support Worker service logs, Coordination Logs, or existing invoice creation logic.

## Navigation

Admin sidebar should keep the current business grouping but make contractor billing explicit:

- Business
  - Invoices
  - Support Items
- Coordination
  - Support Coordinators
  - Coordination Logs
  - SC Invoices

The existing `Invoices` link remains the normal service invoice page. The new `SC Invoices` link opens the support coordination invoice page.

## Page Behavior

The existing `Invoices` list should filter to `Invoice.InvoiceType.SERVICE` by default. Its status cards, filters, pagination, sorting, and row actions should count and display only service invoices.

The new `SC Invoices` list should reuse the existing invoice list table and actions, but filter to `Invoice.InvoiceType.SUPPORT_COORDINATION`. Its heading and helper text should clearly say that this page is for support coordination invoices.

The SC invoice page should include a primary action to create a support coordination invoice, linking to the existing SC invoice creation page.

## Access Rules

Admin and super-admin users can access both `Invoices` and `SC Invoices`.

Accountant users can access only the service invoice list and service invoice detail/export/status actions. Accountant users must not see SC invoices in the service invoice list and must not access the dedicated SC invoice list.

## Testing

Tests should cover:
- Service invoice list excludes support coordination invoices.
- SC invoice list includes support coordination invoices and excludes service invoices.
- Sidebar highlights the correct invoice section.
- Admin can access the SC invoice list.
- Accountant cannot access the SC invoice list.
- Existing service invoice behavior remains covered by the current invoice tests.
