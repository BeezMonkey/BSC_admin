# Phase 40 Roster Name Filters Plan

## Implementation Steps

1. Add tests for roster participant and worker name filtering.
2. Change roster filtering from participant/worker IDs to first-name and last-name text matching.
3. Replace the roster worker dropdown with a worker name search field.
4. Add a participant name search field to the roster filter form.
5. Update existing roster filter tests to use name search.
6. Run focused, module, system, and full Django verification.

## Verification

- Roster filters by participant name.
- Roster filters by worker name.
- Date and status filters still work with name filters.
- Full test suite remains green.
