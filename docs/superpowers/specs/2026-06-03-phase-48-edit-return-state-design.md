# Phase 48 Edit Return State Design

## Goal
Preserve the user's filtered, sorted, and paginated list position when they edit core admin records.

## Scope
This phase covers edit flows for Participants, Support Workers, and Roster shifts. These are the list pages where admin users commonly filter records, open an edit form, and then need to return to the same working set.

Service Logs and Invoices are intentionally excluded from this phase because their update flows are tied to review, billing, and status transitions rather than simple record editing.

## Behavior
List `Edit` links include the current list URL as a `next` parameter. Edit forms validate that return target with the shared safe return helper. The form's `Cancel` links use the safe return target, and successful saves redirect to the same safe return target. If no valid return target is supplied, existing fallback behavior remains unchanged.

## Safety
The implementation reuses `get_safe_return_url` so external redirect targets are ignored. Invalid or missing `next` values fall back to the current detail page for edits.

## Testing
Tests cover the list edit link, edit form cancel link, and successful save redirect for Participants, Support Workers, and Roster shifts.
