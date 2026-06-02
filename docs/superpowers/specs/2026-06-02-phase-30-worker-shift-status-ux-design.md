# Phase 30 Worker Shift Status UX Design

## Goal

Make worker-assigned shifts harder to miss by highlighting status and grouping shifts by action priority.

## Scope

- Add a summary row to My Shifts.
- Group worker shifts into Needs attention, Upcoming, and Completed.
- Show status badges instead of plain status text.
- Visually highlight Published shifts as needing attention.
- Keep existing View-only actions unchanged.

## Behaviour

- Published shifts appear in Needs attention.
- Confirmed shifts appear in Upcoming.
- Completed, Cancelled, and No show shifts appear in Completed/history.
- Draft shifts remain hidden from workers.

## Non-goals

- No new confirm shortcut on the list page.
- No service log shortcut on the list page.
- No change to shift permission rules or status transitions.
