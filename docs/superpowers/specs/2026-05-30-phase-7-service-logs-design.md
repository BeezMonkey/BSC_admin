# Phase 7 Service Logs Design

## Goal

Phase 7 completes the worker-facing operational loop from a scheduled shift to a submitted service log. A support worker can open one of their visible shifts, complete a service log, and submit it for later admin review.

## Scope

This phase includes:

- A `ServiceLog` model linked to one `Shift`.
- Worker service log completion from a published or confirmed shift.
- One service log per shift.
- Submitted service log status.
- Shift status update to `completed` with `completed_at`.
- Worker "My Logs" list and service log detail.
- Admin service log list and detail showing the related shift.

This phase does not include:

- Admin approve or reject actions.
- Invoice generation.
- Manual unrostered service logs.
- File upload, signatures, or incident reporting.

## Data Model

`ServiceLog` stores the submitted record of work:

- `shift`
- `participant`
- `worker`
- `support_item`
- `service_date`
- `actual_start_time`
- `actual_end_time`
- `break_minutes`
- `actual_hours`
- `kilometres`
- `case_notes`
- `worker_notes`
- `status`
- `submitted_at`
- timestamps

Most relationship fields are copied from the shift at submission time so later reporting can remain stable even if the original shift is edited.

## Worker Flow

Workers see a `Complete Service Log` action on their own published or confirmed shifts. The form defaults to the planned shift date, time, break, and planned hours. On submit, the system validates:

- The shift belongs to the logged-in worker.
- The shift is published or confirmed.
- The shift has no existing service log.
- Actual end time is after actual start time.
- Actual hours are greater than zero.

After successful submission, the worker is redirected to the service log detail page.

## Admin Flow

Admins can view all submitted service logs in a list and open a detail page. Review actions remain placeholders for Phase 8.

## Permissions

Workers can only view and create logs for their own shifts. Admins and super admins can view all logs. Accountants do not receive service log access in this phase.

## Tests

Tests cover:

- Worker can complete their own published shift.
- Service log status is `submitted`.
- Shift becomes `completed`.
- A shift cannot create duplicate service logs.
- Worker cannot complete another worker's shift.
- Worker cannot complete a draft shift.
- Worker sees only their own logs.
- Admin can see submitted logs and linked shift detail.
