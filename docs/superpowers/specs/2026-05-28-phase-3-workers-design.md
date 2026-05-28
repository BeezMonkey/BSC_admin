# Phase 3 Support Worker Management Design

## Scope

Phase 3 adds admin-only support worker management and worker login account creation.

Included:
- SupportWorker data model linked one-to-one with Django User.
- Admin-only worker list with search, status filtering, and employment type filtering.
- Worker create form that creates a Django User, UserProfile, and SupportWorker together.
- Worker edit form for profile, contact, employment, and compliance fields.
- Worker detail page.
- Worker profile page for the logged-in support worker.
- Django Admin registration.
- Tests for permissions, account creation, validation, editing, list filtering, detail display, and worker profile access.

Excluded for this phase:
- Participant-worker assignment.
- Worker document upload.
- Payroll, award, and timesheet logic.
- Bank details.
- Availability calendar.
- Compliance file storage.

## Data Model

`SupportWorker` stores the worker's linked login account, contact information, employment information, status, compliance check status/expiry dates, and admin notes.

`status` values:
- `active`
- `inactive`

`employment_type` values:
- `employee`
- `subcontractor`

Compliance status values:
- `not_provided`
- `pending`
- `current`
- `expired`

Creating a worker through the admin worker form also creates:
- a Django `User`
- a `UserProfile` with role `support_worker`
- a `SupportWorker` linked to that user

## Pages

`/workers/`
Admin-only list. Supports search by name, email, and phone. Supports status and employment type filters.

`/workers/new/`
Admin-only create form. Requires username, password confirmation, first name, last name, and email. Email and username must be unique.

`/workers/<id>/`
Admin-only detail page. Shows contact, employment, account status, and compliance overview.

`/workers/<id>/edit/`
Admin-only edit form. Updates User and SupportWorker information without changing the worker's password.

`/sw/profile/`
Support-worker-only page for the logged-in worker to view their own profile.

## Permission Rules

Only Super Admin and Admin can access worker management pages. Support Worker can only access their own `/sw/profile/`. Accountant cannot access worker management or worker profile pages.

## Testing

Tests cover:
- Admin access to worker management pages.
- Worker/accountant denial for admin worker pages.
- Worker-only access to own profile.
- Creating a worker creates User, UserProfile, and SupportWorker.
- Password confirmation validation.
- Unique username and email validation.
- Search and status/employment filters.
- Editing worker information.
- Worker detail page displays compliance information.
