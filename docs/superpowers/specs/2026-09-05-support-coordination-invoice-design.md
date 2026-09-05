# Support Coordination Invoice Design

## Goal

Add an Admin-only invoice workflow for approved Support Coordinator (SC) coordination logs while keeping it separate from the existing Support Worker service-log invoice workflow.

The first version should make approved coordination work billable, downloadable, and traceable without changing the SC portal, Support Worker portal, existing service invoices, roster, service logs, documents, or attachment flows.

## Scope

- Admin users can create invoices from approved coordination logs.
- SC invoices use a dedicated create page and clear Support Coordination labels.
- Approved coordination logs can be selected from the Admin Coordination Logs page.
- Selected coordination logs can be grouped by participant on the SC invoice create page.
- One created invoice belongs to one participant and one billing period.
- A coordination log can only be invoiced once unless the draft/issued invoice is cancelled or a draft invoice is deleted.
- Invoice PDF and CSV downloads work for SC invoices.
- Existing invoice logo, invoice number sequence, payment details, and status workflow are reused.

## Non-Goals

- No invoice features in the SC portal.
- No mixed invoices containing both Support Worker service logs and SC coordination logs.
- No SC invoice access for Support Coordinator users.
- No automatic invoice creation without Admin review.
- No changes to Support Worker invoice behavior.
- No new app packaging or mobile-only interface in this phase.

## Recommended Approach

Extend the existing `Invoice` system with a clear invoice category instead of creating a second invoice app.

Add an `invoice_type` field to `Invoice`:

- `service`, for existing Support Worker service-log invoices.
- `support_coordination`, for SC coordination invoices.

Add a nullable `coordination_log` source field to `InvoiceLine`, while keeping the existing `service_log` source field for current invoices.

Each line must point to exactly one source:

- service invoices use `service_log`.
- support coordination invoices use `coordination_log`.

This keeps invoice numbering, status handling, PDF layout, CSV export, and list/detail pages reusable, but preserves the accounting boundary between SW and SC work.

## Alternatives Considered

### Separate SC Invoice Model

Create new models such as `SupportCoordinationInvoice` and `SupportCoordinationInvoiceLine`.

This gives maximum separation, but duplicates invoice numbers, PDF/CSV generation, status actions, list filters, audit behavior, and payment details. It is heavier than this phase needs.

### Reuse ServiceLog For SC Billing

Convert coordination logs into service logs before invoicing.

This is not recommended because it blurs operational records. SC work should remain in `CoordinationLog`, and SW service delivery should remain in `ServiceLog`.

### Extend Existing Invoice With Source Separation

Use one invoice engine with an `invoice_type` field and mutually exclusive line sources.

This is the recommended path because it is clear, compact, testable, and keeps future reporting manageable.

## Data Model

### Invoice

Add:

- `invoice_type`, choices `service` and `support_coordination`, default `service`.

Rules:

- Existing invoices and future SW invoices default to `service`.
- SC invoice creation always sets `invoice_type=support_coordination`.
- Status choices stay unchanged: draft, issued, paid, cancelled.
- Invoice number sequence stays shared unless a future business requirement asks for separate numbering.

### InvoiceLine

Change:

- Make `service_log` nullable for support coordination lines.

Add:

- `coordination_log`, nullable FK to `coordinators.CoordinationLog`.
- `LineType.SUPPORT_COORDINATION`.

Rules:

- A line cannot have both `service_log` and `coordination_log`.
- A line must have one source.
- A service invoice cannot contain coordination-log lines.
- A support coordination invoice cannot contain service-log lines.
- Add a unique constraint for coordination lines so the same `coordination_log` cannot be billed twice.

### CoordinationLog

Add:

- Status `invoiced`.

Rules:

- Only `approved` coordination logs are billable.
- Creating an SC invoice changes selected logs from `approved` to `invoiced`.
- Cancelling an SC invoice or deleting a draft SC invoice releases linked coordination logs back to `approved`.

## Support Item Selection

SC users should not choose billing support items when submitting coordination logs.

For V1, Admin selects the support item on the SC invoice create page. That support item applies to the selected coordination logs in that invoice group.

This keeps the SC submission form simple and avoids asking SC users to make billing-code decisions. The created invoice line snapshots the selected support item number, description, unit, unit price, GST code, quantity, and line total just like existing service invoices.

## Admin UX

### Coordination Logs List

Add a billing action area to the Admin Coordination Logs page.

Behavior:

- Approved, uninvoiced coordination logs show a checkbox.
- Submitted, rejected, and invoiced logs do not show a billable checkbox.
- The action label should be `Create SC Invoice from Selected`.
- The page should keep its current review purpose and avoid becoming visually busy.

### SC Invoice Create Page

Add a separate page:

- URL name: `support_coordination_invoice_create`.
- Suggested path: `/invoices/support-coordination/new/`.
- Title: `Create Support Coordination Invoice`.

The page should support two entry modes:

- From selected coordination logs.
- From participant, period, and support item filters.

If selected logs belong to multiple participants, the page groups them by participant. Each group has its own `Create Invoice for <Participant>` action.

When creating an invoice from a group:

- Participant is fixed to that group.
- Period is calculated from the earliest and latest selected coordination-log date.
- Admin selects the support item for that group before submit.
- The page creates one invoice for that participant only.

### Invoice List And Detail

The main Invoice list can continue showing both invoice types, but it should make the type visible.

Recommended display:

- Add a small type label, `Service` or `Support Coordination`, near the invoice number or status.
- Add an optional invoice type filter only if the list starts to feel crowded. For V1, visible labels may be enough.

Invoice detail should show:

- Invoice type.
- Existing lines table.
- For SC lines, source date should come from `coordination_log.service_date`.

## PDF And CSV

Reuse the existing invoice logo, payment details, invoice number sequence, totals, and pagination.

SC invoice PDF changes:

- Header title can stay `TAX INVOICE`.
- Add `Invoice Type: Support Coordination`.
- Line item dates come from coordination-log dates.
- Description comes from the selected support item.
- Optional line note can include the coordination type for audit clarity.

Download filename:

- Existing service invoice filename remains unchanged.
- SC invoice PDF/CSV filename should include an SC marker, for example:
  - `SC_Invoice_260905_0034_Demo_Participant.pdf`
  - `SC_Invoice_260905_0034_Demo_Participant.csv`

## Permissions

Use Admin-only access for support coordination invoice creation and support coordination invoice management.

Existing finance/accountant access for Support Worker service invoices stays unchanged.

SC users:

- Cannot access invoice list, invoice create, invoice detail, PDF, CSV, or invoice status actions.
- Do not see invoice links in the SC portal.

Admin users:

- Can create and manage SC invoices through Admin pages.

Finance/accountant users:

- Keep their existing access to Support Worker service invoices.
- Do not get SC invoice access in V1 unless Admin explicitly expands that role later.

## Audit And Messages

Add or reuse audit actions with enough clarity in the summary.

Recommended:

- Add `SUPPORT_COORDINATION_INVOICE_CREATED`.
- Add `SUPPORT_COORDINATION_INVOICE_CANCELLED` only if separate reporting is useful; otherwise reuse `INVOICE_CANCELLED` with the invoice type in the summary.

Messages:

- Success: `Support coordination invoice created.`
- Empty preview: `No approved coordination logs found for this invoice.`
- Duplicate/stale selected log: `Selected coordination logs are no longer available for invoicing.`
- Wrong participant or period on submit: `Selected coordination logs do not match the invoice participant and period.`

## Error Handling

The create page should avoid large red blocking messages for normal workflow friction.

Use clear inline or card messages when:

- No approved coordination logs match the selected filters.
- A selected log was already invoiced by another action.
- A selected log no longer belongs to the selected participant/period.
- The selected support item is inactive or missing.

Creation should run inside a transaction so invoice, lines, audit log, and coordination-log status updates stay consistent.

## Migration Strategy

Migrations should be backward-compatible:

- Existing `Invoice` rows get `invoice_type=service`.
- Existing `InvoiceLine.service_log` rows remain unchanged.
- New nullable `coordination_log` field is added without affecting existing data.
- Add constraints after fields exist.

No data migration is needed for existing coordination logs unless adding the `invoiced` status choice requires only code-level choices.

## Testing

Add focused tests for:

- Admin can preview approved, uninvoiced coordination logs.
- Finance/accountant users cannot create or access support coordination invoices.
- SC users cannot access any invoice pages.
- Submitted/rejected coordination logs are not billable.
- Creating an SC invoice creates support coordination invoice lines.
- Created SC invoice changes selected coordination logs to `invoiced`.
- The same coordination log cannot be invoiced twice.
- Multiple selected participants render separate invoice groups.
- Creating one participant group does not invoice another group.
- Cancelling an SC invoice releases coordination logs back to `approved`.
- Deleting a draft SC invoice releases coordination logs back to `approved`.
- Existing service-log invoice tests still pass.
- Existing service invoice PDF/CSV filenames stay unchanged.
- SC invoice PDF/CSV filenames include `SC_Invoice`.

## Rollout

Implementation should ship as one isolated PR.

Manual smoke test after deploy:

1. Log in as SC and submit a coordination log.
2. Log in as Admin and approve it.
3. Open Coordination Logs and select the approved log.
4. Create a Support Coordination invoice with a support item.
5. Confirm the invoice detail, total, PDF, and CSV.
6. Confirm the coordination log becomes invoiced and cannot be selected again.
7. Confirm an existing SW service-log invoice can still be created and downloaded.

## Open Decision

For V1, the recommended support item behavior is one Admin-selected support item per created SC invoice group.

If SC billing later needs different support items for different coordination types, add per-line support item selection in a later phase instead of complicating this first version.
