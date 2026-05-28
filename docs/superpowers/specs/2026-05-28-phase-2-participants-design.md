# Phase 2 Participant Management Design

## Scope

Phase 2 adds the first real business module: admin-only participant management.

Included:
- Participant data model.
- Admin-only participant list with search and status filtering.
- Participant create form.
- Participant edit form.
- Participant detail page.
- Archive action that preserves historical records.
- Django Admin registration.
- Tests for permissions, validation, creation, editing, filtering, detail display, and archive behavior.

Excluded for this phase:
- Worker-facing participant pages.
- Participant-worker assignment.
- Real roster, service log, invoice, and document tab data.
- File uploads.
- NDIS budget forecasting.

## Data Model

The `Participant` model stores identity, contact, emergency contact, plan, plan manager, support coordinator, worker-visible notes, safety/access notes, internal notes, status, and timestamps.

`status` values:
- `active`
- `inactive`
- `archived`

`management_type` values:
- `ndia_managed`
- `plan_managed`
- `self_managed`

The NDIS number is optional but unique when provided. Archive does not delete the participant.

## Pages

`/participants/`
Admin-only list. Supports search by first name, last name, preferred name, and NDIS number. Supports status filtering. Shows participant name, NDIS number, management type, plan period, support coordinator, status, and actions.

`/participants/new/`
Admin-only create form. Validates required names, email formats, unique NDIS number, plan date order, and Australian postcode format when supplied.

`/participants/<id>/`
Admin-only detail page. Shows overview information and placeholder sections for future roster, service logs, invoices, assigned workers, documents, and notes.

`/participants/<id>/edit/`
Admin-only edit form. Same validation as create.

`/participants/<id>/archive/`
Admin-only POST action. Sets `status=archived` and returns to the participant detail page.

## Permission Rules

Only Super Admin and Admin can access participant pages in this phase. Support Worker and Accountant receive HTTP 403. Unauthenticated users are redirected to login.

## Testing

Tests cover:
- Admin access to participant pages.
- Worker/accountant denial.
- Creating a participant.
- Required first and last name validation.
- Unique NDIS number validation.
- Plan end date cannot be before plan start date.
- Postcode must be four digits when supplied.
- Search and status filters.
- Editing participant details.
- Archive action preserves the record and changes status.
