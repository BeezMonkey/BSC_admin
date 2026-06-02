# Phase 33 Worker Dashboard Summary Design

## Goal

Give support workers a simple dashboard summary that shows which shift items need their next action.

## Scope

- Show counts on the worker dashboard for:
  - Published shifts that need confirmation.
  - Confirmed shifts that are ready for service log completion.
  - Completed or closed shifts.
- Link each count to the matching My Shifts filtered view.
- Keep existing shift, service log, invoice, and admin workflows unchanged.

## Status Mapping

- Published shifts: needs attention.
- Confirmed shifts: ready for log.
- Completed, cancelled, and no-show shifts: completed history.

## Out Of Scope

- Changing shift statuses.
- Adding notifications.
- Changing worker shift list behavior.
