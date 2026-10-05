# Invoice Billing Adjustments

## Approved Scope

Admin may change the whole service's billing support item and confirm missing or corrected kilometres before creating a service invoice. Preserve the original shift/log and hours. Preserve the existing, manually entered Travel claim amount and its fixed travel item/calculation; kilometres never become money automatically. Empty kilometre input keeps the original value; explicit zero means no confirmed kilometres. Blank/zero claim creates no travel line. Community access always offers an optional kilometre entry. Existing recorded-kilometre claims for other service items remain supported.

Only ADMIN_ROLES may submit adjustments; accountants retain the existing flow. A change requires a quick reason, with text required for Other. Rates come from the selected active hourly support item, not arbitrary input. No split service lines, SC changes, worker changes, retrospective invoice editing, or automatic billing classification.

## Architecture And Safety

Use per-log prefixed BillingAdjustmentForm and unchanged TravelClaimForm with an explicitly supplied confirmed-kilometre value. An optional item override on InvoiceLineManager creates invoice snapshots without updating ServiceLog. A separate InvoiceBillingAdjustment model stores original and billed snapshots, reason, actor, time and invoice number. SET_NULL on invoice deletion preserves history; service log detail and invoice detail display it. No automatic reuse after cancellation/deletion.

Create invoices atomically, re-lock and recheck source logs, validate submitted adjustments server-side and prevent duplicate billing. Existing cancellation-charge rows and support coordination paths remain unchanged. UI is scoped to invoice create/history with progressive enhancement and server-side fallbacks.

## Tasks

- [x] 1. Baseline invoice tests; add regression tests for item changes, kilometre correction, permissions, reasons, active/hourly validation, no-op flow, duplicate submission and durable history. Observe failures before implementing.
- [x] 2. Add forms, snapshot model/migration and guarded invoice creation; leave original logs and legacy travel calculations unchanged.
- [x] 3. Add compact per-log adjustment UI and read-only histories, with desktop/mobile verification and no-JS fallback.
- [x] 4. Run full Django/JS tests, migration checks, independent review and isolated browser tests.
- [ ] 5. Commit only scoped code, open and merge a staging PR, verify deployment and hand off staging testing. Do not merge main or upload local demo data.

## Verification Commands

Use the existing project virtualenv with fast test-only password hashing and test-only local storage. Run `manage.py test invoices.tests_billing_adjustments`, full Django tests, `node --test tests/js/*.test.cjs`, `manage.py makemigrations --check --dry-run`, and `git diff --check`. Browser verification covers no adjustment, Self Care to Community Access with missing km, existing travel input, errors/Other, grouping, retained history and mobile width. Test fixtures stay in temporary/local databases.

## Verification Results

- Full Django suite: 837 tests, 835 passed and 2 PostgreSQL-specific lock tests skipped on SQLite.
- JavaScript suite: 39 passed, including 14 billing-interaction tests.
- Migration consistency, static collection and whitespace checks passed.
- Independent backend/frontend review found invoice ordering and decimal preview rounding regressions; both were reproduced with failing tests and fixed before staging.
- Isolated browser test: whole-service item correction with 20 confirmed km and a separately entered 15.50 claim; unchanged existing 48 km with a 25 claim; optional blank km/no claim. Invoice total 460.50 as expected.
- Browser verified desktop and 390px widths, selected-log grouping, Other details, invalid zero-km claim rejection, original log preservation, and history retained after cancellation. Draft deletion retention is covered by Django tests. No browser console errors.
- PostgreSQL concurrency test is included but still needs a PostgreSQL test database to execute; local SQLite cannot verify row-lock behavior.

## Staging Acceptance

1. As Admin, select an approved Self Care log and open Create Invoice. Original item, hours and km must remain visible.
2. Change the whole-service billing item to Community Access. Check the selected rate and unchanged hours; confirm km if needed and enter Travel claim amount independently.
3. Verify blank km/no claim works, while a positive claim without recorded/confirmed km is rejected. Changing item/km requires a reason; Other requires details.
4. Create a draft and compare invoice lines with original log and Billing adjustments history. Cancel/delete a test draft and verify Approved status, available Create Invoice action, and retained history.
5. Confirm existing accountant, worker, cancellation-charge and SC workflows remain unchanged.

Deployment requires `python manage.py migrate` for invoices.0006. This only adds a history table and does not rewrite existing logs or invoices. Local browser demo data is not part of the commit.
