# Phase 6 Basic Scheduling Design

## Scope

Phase 6 adds basic shift scheduling and worker shift confirmation.

Included:
- `Shift` model linked to Participant, SupportWorker, SupportItem, and creator User.
- Admin roster list with filters.
- Admin create, detail, edit, publish, and cancel shift actions.
- Worker shift list.
- Worker shift detail.
- Worker confirm published shift.
- Worker can only see own shifts.
- Worker overlapping active shifts are blocked.
- Tests for permissions, validation, conflict prevention, status changes, and worker access.

Excluded for this phase:
- Recurring shifts.
- Drag-and-drop calendar.
- Completing a shift to ServiceLog.
- Invoice generation.
- Notifications.

## Shift Statuses

- `draft`: admin draft, hidden from worker.
- `published`: visible to worker, waiting confirmation.
- `confirmed`: worker confirmed.
- `completed`: reserved for Phase 7.
- `cancelled`: cancelled with reason.
- `no_show`: reserved for later.

## Conflict Rules

Worker time conflict is blocked for active statuses:
- `draft`
- `published`
- `confirmed`

Cancelled, completed, and no-show shifts do not block new shifts.

End time must be after start time. Planned hours are calculated automatically from start/end minus break minutes.

## Permission Rules

Admin/Super Admin can manage all shifts. Support Worker can only access their own published/confirmed/completed/cancelled/no-show shifts. Draft shifts are hidden from workers.

## Pages

Admin:
- `/roster/`
- `/roster/new/`
- `/roster/<id>/`
- `/roster/<id>/edit/`
- `/roster/<id>/publish/`
- `/roster/<id>/cancel/`

Worker:
- `/sw/shifts/`
- `/sw/shifts/<id>/`
- `/sw/shifts/<id>/confirm/`

## Testing

Tests cover:
- Admin can create draft and published shifts.
- Planned hours are calculated.
- End time before start time is rejected.
- Worker overlap is blocked.
- Worker can see only own published/confirmed shifts.
- Worker cannot see draft shifts.
- Worker can confirm own published shift.
- Worker cannot confirm another worker's shift.
- Admin can cancel shift with reason.
