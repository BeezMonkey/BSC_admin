# Participant Cancellation Review Design

## Goal

Add a simple worker-to-admin cancellation workflow for rostered shifts. A support
worker reports a participant cancellation, an admin reviews it, and an approved
charge uses the original rostered support item, date, planned hours, and rate in
the existing invoice workflow.

The feature must not change ordinary shift completion, service-log review,
unscheduled service, or existing invoice calculations.

## Chosen approach

Create a dedicated cancellation record linked one-to-one with a shift. Do not
create a normal service log for a service that was not delivered, and do not
store the workflow only in free-text shift notes.

This is preferred over reusing `ServiceLog` because service logs require actual
times and case notes and represent delivered support. It is preferred over a
manual invoice-only adjustment because the worker report and admin decision
need a durable audit trail.

## Worker flow

The worker shift detail page shows `Report participant cancellation` for a
published or confirmed scheduled shift that has no service log or cancellation
record.

The compact form contains:

- Cancellation type: `Short notice cancellation` or `No show`.
- Reason: `Health`, `Family issue`, `Transport unavailable`, or `Other`.
- Cancellation details: required free text.
- Cancellation received at: defaults to the submission time and may be adjusted
  when the worker is recording a notification received earlier.

Submitting the form creates the cancellation record with status `Pending
review`. The shift remains linked to its original participant, worker, support
item, date, times, and planned hours. It is marked as awaiting cancellation
review so the worker cannot also submit a normal service log.

The worker sees a concise confirmation and the review state. Billing decisions,
internal claim codes, and admin-only notes are not exposed in the worker portal.

## Admin review

Pending cancellation records appear in a small `Cancellation reviews` workbench
alongside the existing operational workflow. The review screen shows the
original shift, worker submission, notice time, and calculated notice interval.

The admin has three actions:

- `Approve and charge`: accepts the cancellation and makes it invoiceable.
- `Waive charge`: accepts the cancellation but does not make it invoiceable.
- `Reject`: closes an incorrect cancellation report and returns the shift to its
  previous published or confirmed state.

An optional admin note supports audit context. Every decision records the
reviewer and timestamp. Approve and waive set the shift to `Cancelled`; reject
restores the shift's previous state and allows the ordinary workflow to continue.

## Invoice behavior

An approved charge becomes an invoiceable cancellation source. It uses the
original shift's:

- participant;
- service date;
- support item;
- planned hours; and
- applicable support-item rate.

The invoice calculation and totals reuse the existing invoice-line pricing
rules. The invoice line stores an internal cancellation line type and reference
to the cancellation record, so it cannot be invoiced twice.

For the current release, the participant cancellation type, `CANC` claim code,
reason, and cancellation wording are not rendered on the Plan Manager PDF. The
PDF retains the normal support item description and rostered quantity. The
internal line type and cancellation record are deliberately preserved so a
later policy change can expose a cancellation label or claim-code export without
changing historical data.

This display decision is a business choice and does not assert regulatory
compliance. Complete cancellation evidence remains available internally for
review and audit.

## Data and state boundaries

The cancellation record owns:

- shift reference;
- cancellation type and reason;
- worker details and cancellation-received timestamp;
- workflow status;
- admin decision and note;
- submitter, reviewer, submission time, and review time; and
- internal claim type `CANC` for approved charges.

Only one active cancellation record is allowed per shift. An approved or waived
cancellation cannot be edited by the worker. Existing shifts and service logs do
not receive synthetic actual times or case notes.

Normal service invoice lines continue to reference service logs. Cancellation
invoice lines reference cancellation records. Both can appear in the same
participant invoice and use the same totals and PDF layout.

## Guardrails

- Cancellation reporting is limited to the worker assigned to the shift.
- Draft, completed, already cancelled, and unscheduled shifts cannot start this
  workflow.
- A shift cannot have both a service log and a cancellation record.
- Only an admin can approve a charge or waive it.
- Pending, returned, and waived cancellations are excluded from invoice choices.
- Approved cancellations can be invoiced once only.
- Existing conflict detection, worker confirmation, service-log approval,
  travel claims, support coordination, and invoice cancellation behavior remain
  unchanged.

## Interface scope

Keep the feature visually quiet:

- one secondary action on the worker shift detail page;
- one short worker form;
- one pending-review count and list for admins;
- one compact admin review page; and
- small status labels using the existing design system.

No new multi-step wizard, attachment requirement, automatic eligibility engine,
or participant-facing cancellation portal is included.

## Verification

Tests must cover worker permissions, valid shift states, form validation,
duplicate prevention, service-log blocking, all admin decisions, audit fields,
invoice eligibility, planned-hours pricing, duplicate invoicing protection, PDF
non-disclosure, and regression coverage for normal service logs and invoices.

Desktop and mobile checks must confirm that the worker form and admin review
remain compact and that existing shift actions do not move or disappear outside
the cancellation states.
