# Phase 9 Invoice Generation Design

## Goal

Phase 9 creates the first invoice generation loop from approved service logs. Finance users can select a participant and date range, preview approved uninvoiced logs, create an invoice, and view invoice totals.

## Scope

This phase includes:

- `Invoice` and `InvoiceLine` models.
- Invoice creation from approved service logs.
- Participant and date range selection.
- Invoice lines with historical support item values.
- Service logs moving from `approved` to `invoiced`.
- Invoice list and detail pages.
- Finance role access for admin, super admin, and accountant.

This phase does not include PDF/CSV export, payment tracking, void/reissue, credit notes, Xero/PRODA integration, or automated invoice numbering rules beyond a simple local sequence.

## Data Model

`Invoice` stores the billable document:

- `invoice_number`
- `participant`
- `period_start`
- `period_end`
- `status`
- `created_by`
- `created_at`
- `updated_at`

`InvoiceLine` stores historical line values:

- `invoice`
- `service_log`
- `support_item_number`
- `description`
- `unit`
- `unit_price`
- `quantity`
- `gst_code`
- `line_total`

The line values are copied at creation time so later support item price changes do not alter old invoices.

## Invoice Creation Flow

Finance users open the invoice creation page, choose participant and date range, and preview matching logs. Matching logs must be:

- for the selected participant,
- within the date range,
- `approved`,
- not already linked to an invoice line.

Submitting the form creates one invoice and one line per selected approved log. Each related service log is updated to `invoiced`.

## Permissions

Finance access uses the existing finance role rule: super admin, admin, and accountant can access invoices. Workers cannot access invoice pages.

## Tests

Tests cover:

- Finance user can preview approved uninvoiced service logs.
- Finance user can create an invoice from approved logs.
- Invoice lines preserve support item price and description.
- Service logs become `invoiced` after invoice creation.
- Submitted or rejected logs are excluded.
- Already invoiced logs are excluded.
- Worker cannot access invoice generation.
