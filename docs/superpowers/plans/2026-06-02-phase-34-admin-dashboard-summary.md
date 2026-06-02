# Phase 34 Admin Dashboard Summary Plan

## Implementation Steps

1. Add a dashboard regression test for admin operations summary counts and links.
2. Query the dashboard counts from existing Shift, ServiceLog, and Invoice statuses.
3. Render a compact operations summary above the existing admin module cards.
4. Style the summary tiles to match the current dashboard layout.
5. Run focused and full Django verification.

## Verification

- Admin dashboard shows each operations summary count.
- Each summary tile links to an existing filtered list page.
- Existing admin module cards remain visible.
- No workflow state changes are introduced.
