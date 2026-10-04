# SC Log Actions Polish

**Goal:** Keep View and Edit neatly aligned inside the SC log list without changing permissions or other portals.

**Approved design:** Reserve a stable 160px action column, use a compact 8px-gap button group, retain View/Edit labels, and give Edit a pale teal treatment. Keep table scrolling on small screens. No sticky columns, workflow changes, new dependencies or database changes.

**Implementation:** Add a stylesheet loaded only by the SC log list. Scope every rule to `.sc-log-list`, override conflicting shared table widths, and wrap the existing conditional links in a flex group. Preserve existing URLs and `can_coordinator_edit` checks.

## Verification

- [x] Reproduce current overflow in the existing isolated preview: buttons extend 33.7px past their cell.
- [x] Add and run failing template tests for grouped actions, page-only styling, original destinations, empty state and edit eligibility.
- [x] Update the list template and scoped stylesheet; all five focused tests pass.
- [x] Check seven desktop/mobile viewport sizes, wrapped notes, one/two-action rows, horizontal scrolling, and visible keyboard focus. Review hover CSS; no pointer-hover automation was available. View/Edit navigation remains functional, and invoiced records remain read-only.
- [x] Run the full Django suite: 775 tests, 774 passed and one skipped. Inspect the diff and complete independent review with no findings. Provide the local preview on port 8005 without pushing or merging.
