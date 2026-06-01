# Phase 29 Bulk Service Log Invoice Design

## Goal

Reduce missed billing work by allowing finance/admin users to select multiple Approved service logs and create one invoice from the selected records.

## Scope

- Add checkboxes to Approved service log rows.
- Add a Create Invoice from Selected action on the Service Logs page.
- Reuse the existing Create Invoice preview and confirmation page.
- When selected service logs are passed to invoice creation, preview and create only those selected logs.
- Require selected logs to be Approved, uninvoiced, and for one participant.

## Behaviour

The bulk action submits selected `service_log_ids` to the invoice creation page.

If the selected logs are valid:

- The participant field is prefilled.
- The invoice period is set from the earliest to latest selected service date.
- The preview table shows only selected logs.
- The final Create Invoice action creates invoice lines only for selected logs.

If the selected logs are invalid, unavailable, already invoiced, or belong to multiple participants, invoice creation is blocked and the page shows a clear message.

## Non-goals

- No one-click invoice creation from the Service Logs list.
- No mixed-participant invoice creation.
- No change to existing date-range invoice creation.
- No claim submission or payment reconciliation changes.
