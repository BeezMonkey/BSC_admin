# Phase 39 Roster Worker Filter Select Plan

## Implementation Steps

1. Add a regression test for the roster worker dropdown filter.
2. Load active support workers in the roster list view.
3. Replace the worker ID text input with a worker dropdown.
4. Preserve the selected worker after filtering.
5. Run focused, module, system, and full Django verification.

## Verification

- Roster filter shows worker names.
- Selecting a worker filters using the existing worker ID.
- Existing roster filters and summaries remain unchanged.
