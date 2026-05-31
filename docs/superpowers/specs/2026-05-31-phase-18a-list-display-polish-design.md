# Phase 18A List Display Polish Design

Phase 18A fixes visible list-display issues found during V1 trial testing. It focuses on formatting and scanability, not business logic.

## Goals

- Format invoice totals and invoice line amounts to two decimal places.
- Show invoice and service log statuses with the same pill treatment used by other list pages.
- Keep existing links, URLs, permissions, and invoice calculations unchanged.

## Non-goals

- No model changes.
- No database migrations.
- No invoice workflow changes.
- No payment, tax, or accounting logic changes.
- No broad redesign.

## Acceptance Criteria

- Invoice list totals render like `$130.94`, not `$130.940000000000`.
- Invoice detail totals, quantities, unit prices, and line totals use two decimal places.
- Invoice list and service log list statuses use `status-pill`.
- Relevant template tests pass.
