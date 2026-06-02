# Phase 30 Worker Shift Status UX Plan

## Steps

1. Add a failing test for worker shift grouping, summary counts, status badges, and priority ordering.
2. Group worker-visible shifts in the worker shift list view.
3. Render grouped sections in the My Shifts template.
4. Add reusable worker shift list item markup.
5. Add CSS for summary chips, status badges, and attention styling.
6. Run targeted scheduling tests, full Django tests, system check, and browser smoke test.

## Acceptance

- Published shifts are clearly visible under Needs attention.
- Confirmed shifts appear under Upcoming.
- Completed/history shifts are visually lower priority.
- Existing worker shift visibility and confirm flows still pass.
