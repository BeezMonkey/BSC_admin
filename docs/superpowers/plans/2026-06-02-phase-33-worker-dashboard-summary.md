# Phase 33 Worker Dashboard Summary Plan

## Implementation Steps

1. Add a dashboard regression test for worker shift action counts and links.
2. Query the logged-in worker's shifts in the worker dashboard view.
3. Render a shift action summary above the existing worker dashboard cards.
4. Style the summary as compact linked tiles that fit the current worker layout.
5. Run dashboard, scheduling, and full Django test checks.

## Verification

- The worker dashboard shows counts for needs attention, ready for log, and completed shifts.
- Each summary tile links to the matching My Shifts filtered view.
- Existing worker dashboard links remain available.
