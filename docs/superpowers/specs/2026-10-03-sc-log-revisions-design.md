# SC Log Revisions

Approved through the offline preview and workflow discussion on 2026-10-03.

## Scope

Only Support Coordinator logs change. Support Worker forms, permissions, service logs,
cancellations, and service invoices remain unchanged.

SCs may edit their own currently accessible submitted, rejected, or approved logs
when no invoice line references them. Participant and coordinator cannot change.
Saving requires a revision reason and actual content changes, preserves the log ID,
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

Tests cover state transitions, object ownership, assignment removal, role denial,
forged participant, stale tabs/review, invoice associations, atomic audit rollback,
invoice snapshot preservation, and existing SW/invoice regressions. Local test data
must use a separate SQLite database, never a deployed database.
