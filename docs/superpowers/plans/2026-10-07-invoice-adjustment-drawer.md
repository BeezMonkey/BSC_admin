# Invoice Adjustment Drawer Implementation Plan

**Goal:** Implement the approved invoice list/drawer design without changing export formats, automatic rates, cancellation charging, or SC invoicing.

**Architecture:** Retain existing prefixed Django forms and atomic invoice creation. Move the single editable form controls into an accessible dialog when opened and back into their originating form when closed. Keep manual travel amount editable in the list. Admin-only time corrections are validated and saved atomically on invoice creation, with before/after snapshots in existing retained adjustment history. Apply stages changes; it does not perform an independent database write.

**Tech stack:** Django forms/transactions/templates, vanilla JavaScript, existing support-item picker and CSS tokens.

## Steps
- [x] Add failing tests in invoices/tests_billing_drawer.py for corrected times/hours, retained original snapshots, validation, authorization, rollback, cancellation/deletion history, unchanged kilometres, and drawer markup in both invoice flows.
- [x] Extend BillingAdjustmentForm with explicit time-correction opt-in, full validated time fields, and source version. Reuse ServiceLogForm time validation; do not accept client-provided hours or rates.
- [x] Extend billing row preview and atomic creation. Capture original values before correcting log time; create ordinary invoice lines from corrected hours; preserve original item/km/roster. Leave exports untouched.
- [x] Replace inline adjustment layout with a compact rate/hours/km/claim/total table, a drawer partial, and responsive styles. Retain progressive native form fallback and accountant/cancellation access behavior.
- [x] Implement dialog apply/discard, keyboard/focus handling, inline claim synchronization, original values, picker containment, accurate preview totals, and error reopening. No duplicate named controls or automatic km pricing.
- [x] Run focused tests, all invoice tests, planner billing and service-log regressions, Django checks, and browser desktop/mobile flows against isolated local demo data.

## Invariants
- Unchanged kilometre fields use source log values, including omitted/blank POST values.
- A manual travel claim is entered once; list and drawer refer to the same prefixed input.
- Original logs retain item/km; explicit actual-time correction updates time/hours with retained history, not the roster.
- Cancelled/deleted draft invoices release logs; actual-time corrections remain, and their history survives deletion.
- No GitHub push, Staging deployment, or Main merge in this request.

## Verification Notes
- Django invoice, service-log and planner billing suites: 303 tests; 301 passed and 2 PostgreSQL-only concurrency tests skipped on local SQLite.
- JavaScript regression suites: all 76 passed, including 43 drawer tests covering Apply/discard, single-field form ownership, validation, time preview, manual-amount numeric formats and configured travel prices.
- Real local browser: list/drawer claim synchronization, retained km, time correction, Apply/discard, invalid-time blocking, picker containment, form ownership, desktop/mobile layout, invoice creation and retained original-time audit verified.
- Existing CSV and PDF downloads verified from a locally generated demo invoice; corrected 2.75-hour quantity and manual travel amount matched the preview. Export code and formats unchanged.
- Missing/blank source version rejected for opted-in time correction; legacy non-correction submissions remain supported.
- Decimal and exponent number-input forms (.50 and 1e2) normalized for matching preview totals.
- No database migration needed. Demo data lives in a separate temporary local SQLite database, outside the repository.

## Prototype Alignment Follow-up
- Matched drawer header/subtitle, identity/status row, read-only time summary with Correct time/restore controls, item name/code, unit-labelled Travel inputs and footer comparison to the approved HTML preview.
- Kept the existing compact list, real form controls, validation and manual travel-claim semantics unchanged. Original kilometres remain prefilled.
- Added regression coverage for time-entry controls, footer dirty state and support-item display metadata. All 78 JavaScript tests pass; Django suites remain 303 tests, 301 passed and 2 PostgreSQL-only skips.
- Browser verified project selection/reset and accessible names, unchanged-state Apply disabling, desktop layout and 390px mobile layout (drawer scroll width equals client width). No new invoice submitted during this visual follow-up.
- Focused independent review found no actionable regressions. Changes remain local, not pushed.
