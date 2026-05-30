# Phase 8 Service Log Review Design

## Goal

Phase 8 adds the admin review step for submitted service logs. Admin users can approve logs that are ready for invoicing or reject logs that need worker correction or follow-up.

## Scope

This phase includes:

- Admin approve action for submitted service logs.
- Admin reject action for submitted service logs.
- Required rejection reason.
- Review metadata on each service log.
- Worker visibility of rejection reason.
- Admin list filtering by status.
- Tests for review permissions and state transitions.

This phase does not include invoice generation, PDF export, credit notes, editing approved logs, or worker resubmission flows.

## Data Model

`ServiceLog` gains review fields:

- `reviewed_by`
- `reviewed_at`
- `rejection_reason`

`approved` service logs are ready for Phase 9 invoice generation. `rejected` service logs remain visible to the worker with the rejection reason.

## Admin Flow

Admins open a service log detail page. If the log is `submitted`, they can:

- Approve it with a POST action.
- Reject it with a required reason.

Only submitted logs can be reviewed. Approved, rejected, and invoiced logs do not show review actions in this phase.

## Worker Flow

Workers see the status of their logs in My Logs and detail pages. If a log is rejected, the rejection reason is shown on the detail page.

## Permissions

Admin and super admin users can review service logs. Workers cannot call approve or reject endpoints. Accountants do not receive review access in this phase.

## Tests

Tests cover:

- Admin can approve a submitted service log.
- Admin can reject a submitted service log with a reason.
- Reject requires a reason.
- Reviewed metadata is recorded.
- Worker sees rejection reason.
- Worker cannot access review endpoints.
- Approved logs appear in admin status filters.
