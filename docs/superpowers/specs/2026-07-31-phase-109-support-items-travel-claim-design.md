# Phase 109 Support Items and Travel Claim Design

## Goal

Add the three Brisbane Star Care support items currently needed for 2026-27, then allow an administrator to add an approved provider travel non-labour amount while creating an invoice.

The workflow must preserve the existing separation of responsibilities:

- A support worker records actual kilometres in the Service Log.
- The system does not automatically convert kilometres into a claim.
- An administrator decides the final travel claim amount when creating the invoice.
- The invoice keeps the original Service Log as the source record.

## Phase 109A: 2026-27 Support Items

Add an idempotent management command for these verified National price items:

| Item number | Name | Unit | Price |
| --- | --- | --- | ---: |
| `01_011_0107_1_1` | Assistance With Self-Care Activities - Standard - Weekday Daytime | Hour | $73.58 |
| `04_104_0125_6_1` | Access Community Social and Rec Activ - Standard - Weekday Daytime | Hour | $73.58 |
| `04_799_0125_6_1` | Provider travel - non-labour costs | Each | $1.00 |

All three items are active and GST-free. Notes identify the 2026-27 Pricing Schedule v1.2 as the source. The travel item note also states that `$1.00 / Each` is a claim-value mechanism and must not be treated as an automatic `$1 per kilometre` rule.

The command:

- creates missing items;
- updates these three exact item numbers to the verified values;
- does not delete or modify any other Support Items;
- can be run repeatedly without creating duplicates;
- is run explicitly in each environment after deployment.

No database model change is needed for Phase 109A. Administrators can continue creating and editing Support Items manually.

## Phase 109B: Travel Claim at Invoice Creation

### Worker Service Log

The existing `kilometres` field remains the only travel input for support workers. The worker records the total actual kilometres for that service.

Workers do not enter:

- a travel rate;
- a travel claim amount;
- an invoice line.

### Admin Invoice Creation

The approved Service Log preview shows its recorded kilometres. When kilometres are greater than zero, the administrator may enter an optional `Travel claim amount`.

Rules:

- blank or `$0.00` creates no travel line;
- a positive amount creates one travel line for that Service Log;
- the amount must be a valid non-negative monetary value with at most two decimal places;
- kilometres are read-only context and are never automatically converted into money;
- the administrator remains responsible for checking the claim against the service agreement and applicable NDIS rules.

### Invoice Lines

One approved Service Log may generate:

1. one service line using actual hours and the selected support item rate;
2. zero or one provider travel non-labour line.

The travel line uses:

- item number `04_799_0125_6_1`;
- description `Provider travel - non-labour costs`;
- quantity equal to the administrator-approved dollar amount;
- unit price `$1.00`;
- line total equal to the approved dollar amount;
- GST-free treatment.

Example:

- Worker records `43 km`.
- Administrator approves a `$35.00` travel claim.
- Invoice shows `Quantity 35.00 x $1.00 = $35.00`.
- The original `43 km` remains visible through the linked Service Log.

The PDF does not describe the quantity as kilometres because the official support item unit is `Each`, not `Kilometre`.

## Data Model

Change `InvoiceLine.service_log` from a one-to-one relationship to a foreign key so one Service Log can safely produce more than one invoice line.

Add a `line_type` field with two initial values:

- `service`
- `travel_non_labour`

Add a uniqueness constraint on `(service_log, line_type)` so the same Service Log cannot create duplicate service or travel lines.

Existing Invoice Lines are migrated as `service`. Existing invoices, invoice numbers, totals, PDFs, statuses, and links remain unchanged.

No travel amount is stored on the Service Log. The approved amount is stored as the immutable Invoice Line snapshot. If a draft invoice is deleted and recreated, the administrator enters the travel amount again.

## Invoice Creation Behaviour

Invoice creation remains transactional:

- validate selected approved Service Logs;
- validate all entered travel amounts;
- require the travel Support Item when any travel amount is positive;
- create the Invoice;
- create service lines;
- create optional travel lines;
- mark source Service Logs as invoiced;
- roll back the entire operation if any step fails.

If the travel Support Item is missing or inactive, invoice creation shows a clear error and does not create a partial invoice.

## UI Scope

Only the existing Create Invoice preview is extended:

- display recorded kilometres beside each approved Service Log;
- display an optional Travel claim amount input when kilometres are positive;
- clearly label kilometres as worker-recorded context;
- keep the form usable on desktop and mobile;
- preserve all existing participant and date filters.

The Invoice detail page, PDF, and CSV include the added travel line through the existing line-item presentation. No separate travel report or receipt upload is included in this phase.

## Permissions and Audit

- Support workers can record kilometres only.
- Administrators and existing finance-authorized users keep their current invoice permissions.
- Invoice creation audit logging remains in place.
- The resulting Invoice Line provides the approved amount, source Service Log, creator, and creation time through the existing invoice audit trail.

## Tests

Phase 109A tests cover:

- creation of all three verified items;
- exact names, units, prices, GST status, and active state;
- repeated command execution without duplicates;
- unrelated Support Items remaining unchanged.

Phase 109B tests cover:

- worker kilometres remain unchanged;
- blank and zero travel amounts create no travel line;
- positive travel amount creates exactly one travel line;
- travel quantity, unit price, total, item code, and GST are correct;
- one Service Log can create service and travel lines;
- duplicate line types are rejected;
- invalid amounts create no invoice;
- missing or inactive travel item creates no partial invoice;
- existing invoice creation without travel still works;
- invoice detail, PDF, and CSV include travel lines;
- existing Invoice Lines migrate as service lines.

## Out of Scope

- automatic kilometre-to-dollar calculation;
- worker-entered travel amounts;
- receipts or attachment uploads;
- multiple travel expense categories per Service Log;
- parking, toll, or public transport sub-item breakdowns;
- automatic bulk import of the complete NDIS Pricing Schedule;
- changes to existing invoice numbering or PDF branding.

