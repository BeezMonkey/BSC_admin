# SC Log Revisions

Approved through the offline preview and workflow discussion on 2026-10-03.

## Scope

Only Support Coordinator logs change. Support Worker forms, permissions, service logs,
cancellations, and service invoices remain unchanged.

SCs may edit their own currently accessible submitted, rejected, or approved logs
when no invoice line references them. Participant and coordinator cannot change.
Saving requires a selected revision reason and actual content changes, preserves the log ID,
records before/after snapshots, resets review metadata, and resubmits for review.
The previous submission/review remains in history. All date/time/hour validation is
reused from the existing coordination form.

Any existing invoice association (including a draft) or invoiced status locks SC
editing. Existing Admin draft deletion/cancellation and release semantics remain.
Admin can append a correction to invoiced records, retaining original log and invoice
values. Billing corrections are explicitly recorded as requiring invoice review;
this feature does not silently apply them or replace existing invoice actions.

## Safety

Edits, approvals/rejections, and SC invoice creation lock the same log row in a
transaction. Edit and review submissions carry a signed token of log identity and
updated timestamp. Tokens are mandatory; stale or missing tokens do not change data.
Invoice creation rechecks selected records under lock before creating any invoice.
Invoice release also locks source SC logs and rechecks their current status and
invoice membership; a delayed cancellation cannot approve a later revision or
release a log that has entered a different invoice.
History stores actor, time, reason, and structured before/after fields. No sensitive
notes are copied into general audit summaries. Django admin must not bypass this
workflow by editing or deleting coordination logs/history.

The existing explicit trial-demo purge command may delete history only for logs
already selected by its existing demo filters, after `--confirm`. Dry runs and
non-demo history remain unchanged. No live cleanup is run by this implementation.

## UI and Acceptance

Use existing SC form/layout/date controls, add Edit on eligible list/detail rows,
and show revision history on SC/Admin detail pages. Admin review uses the current
version. Invoiced SC details show a read-only message. Admin correction is a separate
form; no SC access. No outbound notifications or new invoice/PDF fields.

The local revision form uses an unselected reason dropdown: Appointment changed,
Correct date / time / hours, Update notes, Address admin feedback, or Other.
Additional details are shown and accepted only for Other, where non-whitespace
details are required server-side. Preset reasons ignore submitted details, even
oversized values. Store the selected label in history.reason and the trimmed
Other details in history.details. Existing free-text history remains readable. Admin
invoiced-record corrections continue to require their existing reason and details.

## Compact Presentation Follow-up

### Single Notes Field

The user approved keeping only the required Case notes input on SC create/edit
forms. Its placeholder is "Record the work completed, outcome, and any follow-up."
using existing muted placeholder styling; it is not an initial value. Existing
coordinator_notes remain stored, visible on SC/Admin details when nonempty, and
included in old and new audit snapshots. They are no longer editable through the
SC form. Excluded legacy notes must not cause a false positive in no-change
validation. Do not migrate or concatenate old notes, modify invoices, or change
Support Worker forms or permissions.

Approved for local preview on 2026-10-03. Scope is presentation only; existing
reason validation, permission checks, resubmission, snapshots and invoice guards
stay unchanged. The revision reason select has a compact desktop width and a
full-width mobile layout. The user's follow-up removes the Add details disclosure:
only Other shows the required details field. Switching reasons preserves the draft
text in the browser, but hidden details are excluded from submission and ignored
server-side. Other validation errors retain the visible text and other form edits.

History remains newest-first, with a collapsed summary showing the action, changed
business fields, actor and time. Expanded entries show the reason, a single compact
Field / Before / After table for changed business fields, and secondary collapsed
Review details for status/reviewer/timestamp changes. Long text shows about three
lines with an accessible full-text toggle; the full original text is retained.
Mobile rows stack before/after without horizontal page overflow. Native disclosures
remain usable without JavaScript, and long text is fully visible without JavaScript.

Tests cover state transitions, object ownership, assignment removal, role denial,
forged participant, stale tabs/review, invoice associations, atomic audit rollback,
invoice snapshot preservation, and existing SW/invoice regressions. Local test data
must use a separate SQLite database, never a deployed database.

## Service Duration Follow-up (2026-10-04)

The approved SC create/edit workflow replaces start/end/break and duplicated
Actual hours inputs with Service duration (integer Hours and Minutes). Duration
must be between 1 and 1440 minutes. Server-side Decimal conversion sets the existing
actual_hours invoice quantity to two decimal places with ROUND_HALF_UP. This
supersedes the earlier SC clock-input validation requirement; Support Worker
forms and invoice code do not change.

Existing clock fields become nullable with no data migration. Previously recorded
times, breaks, notes and snapshots remain intact; new logs do not invent clock
values. Unchanged duration on an existing record preserves its original decimal
quantity, including imported precision. Duration-only edits participate in existing
revision/no-op detection, review reset, audit snapshots and invoice locks.
