# Phase 4 Participant-Worker Assignment Design

## Scope

Phase 4 adds admin-only assignment management between participants and support workers.

Included:
- `ParticipantWorkerAssignment` model.
- Assignment creation from a participant detail page.
- Assignment end action that preserves history.
- Duplicate active assignment prevention.
- Assignment visibility on participant detail and worker detail pages.
- Worker profile page shows assigned participants.
- Tests for permissions, creation, duplicate prevention, end action, and page display.

Excluded for this phase:
- Worker-facing participant detail pages.
- Roster suggestions or automatic scheduling.
- Worker availability.
- Multi-worker service rules.
- Documents linked to assignments.

## Data Model

`ParticipantWorkerAssignment` links one participant to one support worker with:
- `participant`
- `worker`
- `start_date`
- `end_date`
- `is_active`
- `notes`
- timestamps

The model prevents duplicate active assignments for the same participant and worker. Historical inactive assignments are retained.

## Pages and Actions

`/participants/<id>/assign-worker/`
Admin-only assignment creation form. The participant is fixed from the URL. Admin selects a worker, start date, optional end date, active flag, and notes.

`/assignments/<id>/end/`
Admin-only POST action. Sets `is_active=False`, stores an end date, and keeps the record.

Participant detail page:
- Shows active and historical assigned workers.
- Includes an "Assign Worker" action.

Worker detail page:
- Shows active and historical assigned participants.

Worker profile page:
- Shows the logged-in worker's active assigned participants.

## Permission Rules

Only Super Admin and Admin can create or end assignments. Support Worker and Accountant receive HTTP 403 for assignment management routes.

## Testing

Tests cover:
- Admin can create assignment from participant page.
- Duplicate active assignment is rejected.
- End date cannot be before start date.
- Admin can end assignment without deleting it.
- Participant detail displays assigned workers.
- Worker detail displays assigned participants.
- Worker profile displays own assigned participants.
- Worker and Accountant cannot access assignment management routes.
