# Phase 10 Invoice Export Design

## Goal

Phase 10 adds invoice export and basic lifecycle tracking after an invoice has been generated. Finance users can download CSV/PDF files and update invoice status from the invoice detail page.

## Scope

This phase includes:

- Invoice CSV download.
- Invoice PDF download.
- Mark invoice as issued.
- Mark invoice as paid.
- Cancel invoice.
- Finance-role permission checks for all export and status endpoints.
- Tests for response formats, exported data, and status transitions.

This phase does not include email sending, branded PDF polish, Xero/PRODA integration, credit notes, void/reissue flows, or editing invoiced service logs.

## CSV Export

CSV export returns a downloadable file with invoice header fields and one row per invoice line. It includes:

- invoice number
- participant
- period start
- period end
- status
- support item number
- description
- unit
- quantity
- unit price
- GST code
- line total

The CSV uses historical `InvoiceLine` values, not current `SupportItem` values.

## PDF Export

PDF export returns a simple PDF containing invoice number, participant, period, status, line items, and total. The first version is functional rather than branded; visual polish can happen after the business flow is stable.

## Status Flow

Finance users can update:

- `draft` -> `issued`
- `issued` -> `paid`
- `draft` or `issued` -> `cancelled`

Cancelled and paid invoices cannot be changed further in this phase.

## Permissions

All Phase 10 endpoints use the existing finance role rule: super admin, admin, and accountant can access them. Workers cannot access invoice exports or status actions.

## Tests

Tests cover:

- CSV download content type and rows.
- PDF download content type and PDF header.
- Finance user can mark invoice issued.
- Finance user can mark invoice paid.
- Finance user can cancel invoice.
- Worker cannot download invoice CSV.
