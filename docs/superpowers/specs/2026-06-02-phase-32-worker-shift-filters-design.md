# Phase 32 Worker Shift Filters Design

## Goal

Help workers focus on the relevant shift group when the My Shifts list grows.

## Scope

- Add filter chips to My Shifts: All, Needs attention, Upcoming, Completed.
- Preserve the summary counts for all visible worker shifts.
- Filter only the displayed groups; do not change shift permissions, status transitions, or actions.

## Behaviour

The `view` query parameter controls the displayed shift group:

- `all` shows all groups.
- `needs_attention` shows Published shifts.
- `upcoming` shows Confirmed shifts.
- `completed` shows Completed, Cancelled, and No show history.

Invalid values fall back to `all`.

## Non-goals

- No search by participant/date.
- No dashboard summary changes.
- No collapsing sections.
