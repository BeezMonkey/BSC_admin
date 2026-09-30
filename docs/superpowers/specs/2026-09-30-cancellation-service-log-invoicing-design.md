# Cancellation Charges in the Service Logs Billing Workbench

## Goal

Allow admins to prepare one participant invoice from the Service Logs workbench when the invoice contains both approved service logs and approved participant cancellation charges. Keep cancellation review and audit records separate, and keep cancellation metadata off the customer-facing invoice and PDF.

## Current Behaviour

- A worker reports a participant cancellation against a rostered shift.
- Admin approval changes the `ParticipantCancellation` to `approved` and the shift to `cancelled`.
- Approval does not create a `ServiceLog`.
- The cancellation detail page links to invoice creation by participant and service date.
- Manual invoice creation by participant and date already includes approved, uninvoiced cancellations.
- Service Logs bulk invoicing only submits `service_log_ids`, so selected service logs cannot currently be combined with selected cancellation charges.

## Approved Design

### Data ownership

`ParticipantCancellation` remains the source of truth for cancellation type, reason, details, review note, reviewer, and review timestamps. The implementation must not create a synthetic `ServiceLog` and must not copy private cancellation details into invoice notes.

### Service Logs workbench

When the active status card is `Approved`, the Billing action area will also show approved, uninvoiced participant cancellations that match the current Participant and Service Date filters.

Cancellation charges will appear in the same admin-only billing table as approved service logs, sorted and paginated with the service-log rows. Each row will show:

- selectable checkbox;
- rostered service date;
- participant;
- worker;
- `Approved` status;
- rostered hours;
- neutral admin text such as `Approved rostered charge`, using a subtle text colour to distinguish it from delivered-service notes.

The row will not show cancellation type, reason, worker-entered details, claim code, or admin review note. The existing Cancellation page remains the place for reviewing those details.

Cancellation rows will not be added to Submitted, Invoiced, Rejected, or the unfiltered All Logs history. This keeps Service Logs history semantically accurate while making the Approved view a complete billing workbench.

The existing participant and service-date filters apply to both datasets. An invalid or unknown participant produces no cancellation matches, consistent with service-log filtering.

### Selection and invoice preview

The Billing action form will submit:

- `service_log_ids` for checked service logs;
- `participant_cancellation_ids` for checked cancellation charges.

Selected records are explicit. If the admin selects only service logs, unrelated cancellation charges in the same date range are not silently added. If both record types are selected, they are grouped by participant using the existing multi-participant preview pattern.

For each participant group:

- the invoice period spans the earliest to latest selected service date across both record types;
- total hours include service-log actual hours and cancellation rostered hours;
- the preview contains both service rows and cancellation rows;
- hidden inputs preserve both ID collections through POST.

A cancellation-only selection is valid. POST validation requires every selected cancellation to remain approved and uninvoiced, and all records in one submitted invoice group to belong to the form participant and period. Stale or mismatched selections return a clear error and do not create a partial invoice.

### Invoice creation and output

Invoice creation continues to use `InvoiceLine.objects.create_from_participant_cancellation()` for cancellation rows. The existing unique constraint prevents double billing.

The customer-facing Invoice and PDF remain unchanged:

- show the normal support item, service date, rostered hours, rate, and amount;
- do not show `CANC`;
- do not show `Short notice cancellation`;
- do not show cancellation reason, details, or review notes.

### Existing entry points

The Cancellation detail page keeps its current Create Invoice shortcut. Manual invoice creation by participant and period continues to include all approved, uninvoiced cancellation charges in the selected period. This change adds the missing Service Logs bulk-selection path without removing working paths.

## Alternatives Considered

### Create a synthetic Service Log

Rejected because it would misrepresent a cancellation as delivered support, duplicate source data, and weaken the audit trail.

### Automatically add every cancellation in the selected date range

Rejected for Service Logs bulk invoicing because checkbox selection should remain explicit and predictable. Manual participant/date invoice creation retains its existing automatic inclusion behaviour.

### Keep invoicing only on the Cancellation page

Rejected because it fragments the normal admin billing workflow and prevents one deliberate selection from combining delivered services and cancellation charges.

## Testing

Automated coverage will verify:

- approved, uninvoiced cancellations appear only in the Approved Service Logs billing area;
- participant and service-date filters apply to cancellation rows;
- pending, waived, rejected, and already invoiced cancellations do not appear;
- selected cancellation IDs survive GET preview and POST;
- cancellation-only and combined service/cancellation invoices are created correctly;
- multi-participant selections are grouped correctly;
- stale or mismatched selections are rejected atomically;
- invoice and PDF output still hide cancellation metadata;
- existing service-log approval, cancellation review, manual invoice, sorting, and pagination behaviour remain unchanged.
