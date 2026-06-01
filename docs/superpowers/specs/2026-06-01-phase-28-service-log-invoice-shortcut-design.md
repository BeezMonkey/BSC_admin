# Phase 28 Service Log Invoice Shortcut Design

## Goal

Reduce missed or repetitive invoice creation work by letting finance/admin users start an invoice directly from an Approved service log.

## Scope

- Add a Create Invoice action to Approved service log rows.
- The shortcut opens the existing invoice creation page.
- The invoice creation page is prefilled with the service log participant and the service log date as both period start and period end.
- The existing invoice preview and confirmation step remains unchanged.

## Behaviour

The shortcut URL passes:

- `participant`
- `period_start`
- `period_end`

Submitted, Rejected, and Invoiced service logs do not show the shortcut.

## Non-goals

- No single-click invoice generation from the service log list.
- No multi-select invoice creation.
- No change to invoice calculation, export, cancellation, or deletion rules.

## Future Option

A later phase can add multi-select invoice creation for multiple Approved service logs, with validation that selected logs belong to the same participant and are still uninvoiced.
