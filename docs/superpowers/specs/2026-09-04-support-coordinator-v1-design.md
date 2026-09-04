# Support Coordinator V1 Design

## Goal

Add a first version of Support Coordinator (SC) functionality without changing the current support worker, roster, service log, document, or invoice workflows.

SC users get their own portal. Admin users manage SC accounts, assign participants to SC users, and review SC-submitted coordination logs. SC users cannot access the Admin portal, and support workers cannot access the SC portal.

## Scope

This phase builds only the operational foundation:

- Admin can create, edit, view, and deactivate support coordinator profiles.
- Admin can assign active participants to active support coordinators.
- SC users can log in to a separate SC portal.
- SC users can see only their assigned participants.
- SC users can submit coordination logs for assigned participants.
- Admin can list, view, approve, and reject coordination logs.

This phase does not add SC invoicing, SC roster shifts, open shifts, availability, service log billing, document attachments, PDF export, or mobile app packaging.

## Existing System Fit

The current app already has three important patterns to reuse:

- `accounts.UserProfile.Role` controls portal identity.
- `accounts.decorators.role_required` provides role-based access gates.
- `participants.ParticipantWorkerAssignment` shows the existing assignment style for limiting worker access to participants.

SC should follow these patterns instead of sharing Admin permissions or reusing support worker models. The existing `Participant.support_coordinator_name`, email, and phone fields remain as external contact fields; they are not a system login or assignment mechanism.

## Roles And Permissions

Add a new `support_coordinator` role to `UserProfile.Role`.

Define:

- `SUPPORT_COORDINATOR`
- `COORDINATOR_ROLES = (SUPPORT_COORDINATOR,)`
- `coordinator_required = role_required(*COORDINATOR_ROLES)`

Login redirects become:

- Admin and Super Admin -> Admin dashboard
- Support Worker -> Worker dashboard
- Support Coordinator -> SC dashboard
- Accountant -> invoice placeholder

Every SC route must use `coordinator_required`. Every admin SC-management and coordination-log review route must use `admin_required`.

## Data Model

### SupportCoordinator

Stores the internal SC profile linked to a Django user.

Fields:

- `user`, one-to-one with auth user
- `first_name`
- `last_name`
- `email`, unique
- `phone`, optional
- `status`, active or inactive
- `notes`, optional
- `created_at`
- `updated_at`

Sorting should follow the worker pattern: last name, then first name.

### ParticipantCoordinatorAssignment

Connects participants to SC users.

Fields:

- `participant`
- `coordinator`
- `start_date`
- `end_date`, optional
- `is_active`
- `notes`, optional
- `created_at`
- `updated_at`

Rules:

- A participant can have at most one active assignment to the same coordinator.
- SC portal queries only use active assignments for active participants and active coordinators.
- Ending an assignment removes future SC portal access to that participant, but historical coordination logs remain visible to Admin.

### CoordinationLog

Stores SC-submitted records separately from worker `ServiceLog`.

Fields:

- `participant`
- `coordinator`
- `service_date`
- `start_time`
- `end_time`
- `break_minutes`
- `actual_hours`
- `coordination_type`, simple choice list
- `case_notes`
- `coordinator_notes`, optional
- `status`, submitted, approved, or rejected
- `reviewed_by`, optional admin user
- `reviewed_at`, optional
- `rejection_reason`, optional
- `submitted_at`
- `created_at`
- `updated_at`

Ordering should be newest first: service date descending, then submitted time descending.

The first coordination type choices should be simple and operational:

- General coordination
- Participant / family contact
- Provider contact
- Plan review / funding discussion
- Incident or concern follow-up
- Other

## Admin Experience

### Support Coordinators

Add an Admin sidebar item under Operations: `Support Coordinators`.

Admin list page:

- Shows name, email, phone, status, active participant count, and actions.
- Supports status filtering and keyword search.
- Uses the same table/card rhythm as Support Workers.

Admin detail page:

- Shows SC profile details.
- Shows active and historical participant assignments.
- Provides assign-participant action.
- Keeps profile editing separate from assignment actions.

### Coordination Logs

Add an Admin sidebar item under Operations: `Coordination Logs`.

List page:

- Shows submitted coordination logs with status filters.
- Columns: date, participant, support coordinator, coordination type, hours, status, notes preview, actions.
- Defaults to newest first.

Detail page:

- Shows coordination details and notes.
- Review area supports approve and reject.
- Rejection requires a reason.
- Uses success/error messages consistent with service log review.

This page must not expose `Create Invoice` actions in V1.

## SC Portal Experience

Create a separate SC base template rather than reusing Admin navigation. It can reuse the support worker mobile shell pattern, but labels and links should be SC-specific.

SC navigation:

- Dashboard
- My Participants
- My Coordination Logs
- Profile

SC dashboard:

- Shows lightweight summary cards: assigned participants, submitted logs, approved logs, rejected logs.
- Primary action: `Submit Coordination Log`.
- Keeps the screen simple for mobile-first use.

My Participants:

- Lists only actively assigned participants.
- Shows participant name, address/suburb, phone, and worker-visible notes where appropriate.
- Does not expose internal admin notes.

My Coordination Logs:

- Lists only the current SC user's own logs.
- Shows date, participant, type, hours, and status.
- Allows viewing detail.

Submit Coordination Log:

- Participant selector includes only actively assigned participants.
- Required fields: participant, date, start time, end time, break, coordination type, case notes.
- Optional fields: coordinator notes.
- On submit, create a `submitted` log and show a success message.

## UX Direction

SC portal should be practical and mobile-first, not visually heavy.

Use the same brand foundation as the worker portal:

- existing green/teal primary action color
- existing surface, border, and card tokens
- bottom navigation on mobile, with no more than four items
- touch targets at least 44px high
- clear form labels and inline validation

Because this is a work tool, do not make the SC dashboard decorative. Prioritize clear actions, status visibility, and fast record entry.

## Data Flow

Admin setup flow:

1. Admin creates a support coordinator profile and linked user.
2. Admin assigns one or more participants to the SC.
3. SC logs in through the SC portal.
4. SC sees only assigned participants.

Coordination log flow:

1. SC submits a coordination log for an assigned participant.
2. The log is created with `submitted` status.
3. Admin reviews the log.
4. Admin approves it or rejects it with a reason.
5. The log remains separate from service logs and invoices.

## Audit And Messages

Add audit entries for:

- Support coordinator created
- Support coordinator updated
- Participant assigned to support coordinator
- Coordination log submitted
- Coordination log approved
- Coordination log rejected

Use existing message patterns:

- SC submit success: `Coordination log submitted for admin review.`
- Admin approve success: `Coordination log approved.`
- Admin reject success: `Coordination log rejected.`
- Missing rejection reason: `Rejection reason is required.`

## Testing

Add tests for:

- SC role redirects to the SC dashboard.
- SC user cannot access Admin routes.
- Admin can access SC management and coordination-log review routes.
- Support Worker cannot access SC routes.
- SC participant list contains only actively assigned participants.
- SC cannot submit a coordination log for an unassigned participant.
- SC can submit a valid coordination log for an assigned participant.
- Admin can approve submitted coordination logs.
- Admin can reject submitted coordination logs only with a reason.
- Existing worker service log, roster, invoice, and document tests still pass.

## Safety Boundaries

Implementation must avoid these changes in V1:

- Do not add SC records into `ServiceLog`.
- Do not add SC logs into invoice selection.
- Do not allow SC users into Admin.
- Do not allow Admin-only participant internal notes into the SC portal.
- Do not change support worker login, dashboard, service log, roster, attachment, document, or invoice behavior.

## Future Work

These are deliberately outside V1:

- SC invoice workflow.
- Coordination log PDF export.
- Coordination log attachments.
- SC availability or scheduling.
- SC mobile app packaging.
- Deeper dashboard analytics.
