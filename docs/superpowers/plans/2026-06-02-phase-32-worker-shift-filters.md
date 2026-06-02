# Phase 32 Worker Shift Filters Plan

## Steps

1. Add failing tests for worker shift group filtering and filter navigation.
2. Read `view` from the My Shifts query string.
3. Keep all summary counts based on the worker-visible shift set.
4. Render only the selected shift group when a specific filter is active.
5. Add filter chip styling.
6. Run scheduling tests, full Django tests, and system check.

## Acceptance

- Workers can switch between All, Needs attention, Upcoming, and Completed.
- Needs attention only displays Published shifts.
- Upcoming only displays Confirmed shifts.
- Completed only displays history-style shifts.
- Existing quick actions remain available in the relevant filtered view.
