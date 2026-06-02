# Phase 35 Dashboard Plural Labels Plan

## Implementation Steps

1. Add a regression test for plural admin dashboard summary labels.
2. Add a small count label helper in the dashboard view layer.
3. Render generated labels in the admin dashboard template.
4. Run focused dashboard tests, Django system checks, and full test coverage.

## Verification

- Singular labels still display correctly for count 1.
- Plural labels display correctly for count 2 or more.
- Existing summary links remain unchanged.
