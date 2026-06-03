# Phase 51 Status Pill Colors Design

## Goal
Make record statuses easier to scan by giving status pills consistent semantic colors across admin lists and detail panels.

## Scope
This phase updates existing status pill classes and CSS only. It does not change models, status values, workflows, permissions, or persistence.

Covered areas:

- Participants
- Support Workers
- Roster shifts
- Service Logs
- Invoices
- Support Items
- Detail status panels that already render status pills

## Behavior
Templates add `status-<value>` classes to status pills. CSS maps common status values to semantic colors:

- Active, approved, confirmed, issued, paid, current: green
- Draft, archived, inactive, not provided, completed: grey
- Published, submitted, pending: amber
- Rejected, cancelled, no show, expired: red
- Invoiced: teal

## Testing
Template tests verify that representative list pages render status-specific classes. Existing app tests verify behavior remains unchanged.
