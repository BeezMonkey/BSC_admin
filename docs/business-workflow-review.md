# Business Workflow Review

This document reviews the current V1 business workflow for the Brisbane Star Care NDIS admin system.

Phase 25 is a review phase only. It does not add features, change fields, or change permissions.

## Overall Assessment

The current V1 supports the core local trial workflow:

1. Admin creates participants and workers.
2. Admin assigns workers to participants.
3. Admin creates support items.
4. Admin creates and publishes roster shifts.
5. Worker views assigned shifts.
6. Worker confirms shifts and submits service logs.
7. Admin reviews service logs.
8. Finance/admin creates invoices from approved logs.
9. Admin exports invoice CSV/PDF.
10. Admin uploads and downloads documents.
11. Audit logs record selected key actions.

This is a coherent V1 operations loop. The main remaining gaps are workflow convenience, reporting, notifications, and deeper real-world business rules.

## Participant Workflow

### Current Flow

- Admin opens Participants.
- Admin creates a participant record.
- Admin can edit participant details.
- Admin can assign a worker from the participant detail page.
- Admin can archive a participant.

### Working Well

- Participant core details, contact details, NDIS details, plan manager details, support coordinator details, worker-visible notes, risk notes, and internal notes are already represented.
- Participant detail is a good anchor point for assignment and future related information.

### Friction Points

- After creating a participant, the next recommended steps are not explicitly guided.
- There is no checklist showing whether a participant is ready for rostering.
- Plan expiry and missing NDIS/plan fields are not highlighted.

### Suggested Future Improvements

- Add a participant readiness panel on detail pages.
- Add shortcuts from participant detail to create assignment, upload document, or create shift.
- Add plan expiry warnings.
- Consider participant status filters such as active onboarding, active service, inactive, archived.

## Support Worker Workflow

### Current Flow

- Admin opens Support Workers.
- Admin creates a support worker and linked user account.
- Admin can edit worker details and compliance status.
- Worker can log in and view their profile.

### Working Well

- Worker records include employment type, status, police check, WWCC/Blue Card, expiry dates, and notes.
- Worker profile is visible to the worker.
- Admin can see assigned participants from worker detail.

### Friction Points

- Compliance expiry dates are stored but not surfaced as warnings.
- New worker onboarding does not show a ready/not-ready status.
- Worker availability is not represented yet.

### Suggested Future Improvements

- Add compliance warning badges for expired or soon-expiring checks.
- Add worker onboarding/readiness checklist.
- Add worker availability or preferred hours if rostering needs it.
- Add worker document upload shortcuts.

## Assignment Workflow

### Current Flow

- Admin assigns a worker to a participant.
- Active duplicate assignment for the same participant-worker pair is prevented.
- Admin can end an assignment.
- Participant and worker detail pages show assignment context.

### Working Well

- The assignment concept is clear and useful for future workflow rules.
- Active/inactive assignment history is retained.

### Friction Points

- Roster creation does not yet enforce that the chosen worker is actively assigned to the participant.
- Assignment notes are not used to guide roster or worker pages.

### Suggested Future Improvements

- Warn when creating a shift for a worker who is not assigned to the participant.
- Use assignment notes in roster context if operationally helpful.
- Add assignment start/end warnings when roster dates fall outside the assignment period.

## Roster Workflow

### Current Flow

- Admin creates one-off shifts.
- Admin creates recurring draft shifts.
- Admin publishes draft shifts.
- Worker sees published, confirmed, completed, cancelled, and no-show shifts.
- Worker confirms published shifts.
- Worker submits service logs from eligible shifts.
- Admin can cancel shifts.

### Working Well

- Draft to published to confirmed/completed is a sensible V1 state flow.
- Recurring shift creation already checks worker conflicts.
- Worker pages are separated from admin-only roster pages.

### Friction Points

- Roster is table/list based, not calendar based.
- There is no daily/weekly roster view.
- Shift publish is per-shift only.
- No notification is sent when a shift is published or changed.
- There is no explicit no-show workflow yet.

### Suggested Future Improvements

- Add week/day roster views.
- Add bulk publish for draft shifts.
- Add shift change notifications later.
- Add no-show handling if required.
- Add roster warnings for missing support item, missing assignment, expired worker compliance, or inactive participant/worker.

## Worker Service Log Workflow

### Current Flow

- Worker opens My Shifts.
- Worker opens a shift.
- Worker submits a service log for published or confirmed shifts.
- Submission marks the shift as completed.
- Worker can view submitted logs from My Logs.

### Working Well

- Service log pulls participant, worker, support item, and date from the shift.
- A shift can only have one service log.
- Actual hours, kilometres, case notes, and worker notes are captured.

### Friction Points

- Workers can submit logs for published shifts even if they have not confirmed first.
- There is no draft service log state.
- Rejected logs are visible, but the edit/resubmit loop is not yet implemented.

### Suggested Future Improvements

- Decide whether worker confirmation should be mandatory before service log submission.
- Add resubmission workflow for rejected logs.
- Add stronger guidance for required case note quality.
- Add late/missing service log reporting.

## Admin Service Log Review Workflow

### Current Flow

- Admin opens Service Logs.
- Admin filters by status.
- Admin opens log detail.
- Admin approves or rejects submitted logs.
- Rejection requires a reason.
- Approved logs become invoice-ready.

### Working Well

- Review state is clear: submitted, approved, rejected, invoiced.
- Approval/rejection is audited.
- Rejection reason is required.

### Friction Points

- No bulk approval.
- No side-by-side comparison of planned shift hours versus actual log hours.
- No warning for unusually high hours or kilometres.

### Suggested Future Improvements

- Add planned versus actual comparison on service log detail.
- Add review flags for large differences.
- Add bulk approval for low-risk logs later.
- Add reporting for rejected logs and pending review logs.

## Invoice Workflow

### Current Flow

- Finance/admin opens Invoices.
- Finance/admin creates an invoice by participant and period.
- Only approved, uninvoiced service logs are included.
- Service logs become invoiced after invoice creation.
- Invoice can move from draft to issued to paid.
- Draft or issued invoice can be cancelled.
- CSV and simple PDF exports are available.

### Working Well

- Invoice creation is linked to approved service logs.
- Duplicate invoicing is prevented by the one-to-one invoice line link.
- CSV export is practical for early operations.
- Invoice status progression is clear.

### Friction Points

- Cancelled invoices do not currently release the related service logs back to approved.
- Invoice totals and PDF output are intentionally simple.
- There is no claim/payment reconciliation beyond issued/paid.
- There is no bulk invoice generation for all participants in a period.

### Suggested Future Improvements

- Decide whether cancelling an invoice should restore service logs to approved.
- Add invoice preview summary before final create.
- Add bulk invoice generation by period.
- Improve PDF formatting later.
- Add payment reference and paid date fields when finance workflow requires it.

## Document Workflow

### Current Flow

- Admin uploads documents.
- Documents can be linked to participant, worker, invoice, or service log.
- Admin can download documents.
- Worker can view/download documents linked directly to their worker record.

### Working Well

- Document categories cover plans, compliance, invoices, service logs, and general files.
- Download actions are protected by role.
- Upload/download actions are audited for admin side.

### Friction Points

- Worker can only see worker-linked documents, not participant documents for assigned participants.
- There is no document expiry date.
- There is no document search or filter yet.
- There is no antivirus scanning or external storage integration.

### Suggested Future Improvements

- Add filters for category, participant, worker, and date.
- Add expiry dates for compliance/plan documents.
- Decide whether workers should see participant documents for assigned participants.
- Add storage and backup rules before production.

## Audit Log Workflow

### Current Flow

- Admin can view audit logs.
- Key actions are logged for service log review, shift cancellation, invoice actions, and document upload/download.

### Working Well

- The current audit log covers important high-risk actions.
- Audit detail page supports traceability.

### Friction Points

- Create/edit actions for participant, worker, support item, and shift are not all audited yet.
- Login/logout events are not audited.
- Audit logs do not include before/after field changes.

### Suggested Future Improvements

- Expand audit coverage for create/edit/archive actions.
- Add login and failed-login audit records if needed.
- Add before/after summaries for sensitive edits later.
- Add audit filters by actor, action, date, and object type.

## Recommended Next Phases

Recommended order:

1. **Phase 26: Workflow Shortcuts And Readiness Panels**
   Add practical next-step prompts and shortcuts on participant, worker, and shift detail pages.

2. **Phase 27: Compliance And Plan Expiry Alerts**
   Surface worker compliance expiry and participant plan expiry warnings.

3. **Phase 28: Service Log Review Enhancements**
   Add planned-versus-actual comparison and review warning flags.

4. **Phase 29: Invoice Cancellation And Finance Rules Review**
   Decide and implement how invoice cancellation should affect invoiced service logs.

5. **Phase 30: Reporting And Operational Dashboards**
   Add summary views for pending service logs, upcoming shifts, expiring compliance, and invoice status.

## Recommendation

Before large UI theme integration or production deployment, improve workflow guidance and operational warnings. The current V1 flow is coherent, but the next value comes from making daily operations easier and safer.
