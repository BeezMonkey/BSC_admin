# Planner Billing Check Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. Keep financial data read-only and preserve unrelated worktree changes.

**Goal:** Add the approved compact billing-status row and right-side detail drawer to all three Quick Roster Planner views.

**Architecture:** An Admin-only GET endpoint renders a fresh server-side HTML partial. A read-only projection module resolves existing Shift -> ServiceLog/ParticipantCancellation -> InvoiceLine relations; no new persisted data or financial decisions. Billing mode and filter are URL parameters, preserved across week/view/filter navigation. Disabled mode leaves cards unchanged and does not load invoice details.

**Tech Stack:** Django ORM/templates, scoped CSS, native dialog, vanilla JavaScript, Django tests and node:test.

## Approved Scope

- Default off. Enabled cards add one compact line; no invoice numbers or amounts on cards.
- Desktop drawer 456px, overlay rather than calendar reflow; mobile full width.
- Distinct rostered, actual and invoiced hours, including break-aware original time ranges. Approximate minute differences derive from stored decimal hours; cancellation actual hours are not invented.
- Actual hours may be shown as pending/rejected, never as approved implicitly.
- Invoice Draft, Issued and Paid remain distinct. Cancelled invoices do not count as active invoices. Missing/inconsistent records require review rather than inferred billing.
- Show original roster/log items and actual invoice line snapshots, not today's catalogue price; show adjustment history and confirmed km only when tied to the current active invoice.
- Service and travel lines are separated; shift total is not whole-invoice total. No multiplication of km into a monetary claim.
- Include cancellation pending, approved, waived and rejected paths. Do not flag future, draft or cancelled shifts as missing logs.
- Preserve all existing copy/edit/view/delete/modal, holiday, conflict and worker-workload behavior.
- No mutations, migration, export, new access roles, production data or demo data in the feature patch.

## Tasks

### 1. Data projection (delegated write scope)

Files: `scheduling/planner_billing.py`, `scheduling/tests_planner_billing_data.py`.

- [x] Write failing tests using real ORM records for status precedence, service/travel separation, snapshots, cancelled invoices, km adjustments, missing/future logs, cancellation states, and bounded query count.
- [x] Add `with_billing_relations(queryset, detail=False)`, `billing_summary(shift, now=None)` and `billing_detail(shift, now=None)` with no writes.
- [x] Run `manage.py test scheduling.tests_planner_billing_data` with isolated test DB and verify no source changes.

### 2. Planner and GET endpoint

Files: `scheduling/views.py`, `scheduling/urls.py`, `scheduling/billing_views.py`, `scheduling/tests_planner_billing.py`.

- [x] First add failing tests: off mode contains no status rows; enabled mode supports every planner view; role checks deny Worker/SC/Accountant; detail rejects POST; HTML escapes record names; filters preserve people/date/week/view.
- [x] Parse `billing=1` and allowlisted `billing_status`. Attach projected summaries only when enabled; filter display shifts after workload/conflict calculations. Preserve context on generated navigation URLs.
- [x] Add `/roster/planner/<shift_id>/billing/` with `admin_required`, `require_GET`, `never_cache`, a standalone fallback page and an explicitly requested partial response for the drawer.
- [x] Re-run regression tests for planner hours, conflict and cancellation behavior.

### 3. Scoped UI and request lifecycle

Files: `templates/scheduling/roster_planner.html`, `_planner_shift_tile.html`, `partials/planner_billing_content.html`, `planner_billing_detail.html`, `static/css/planner_billing.css`, `static/js/planner_billing.js`, `tests/js/planner_billing.test.cjs`.

- [x] Test lifecycle: open/load/error/retry/close, obsolete request ignored, expired login not injected, focus restoration and previous/next visible shift.
- [x] Add native dialog with stable header/footer and independently scrolling body. Escape/backdrop/close restore focus; abort requests on close, retry or next/previous. Never present network failure as an uninvoiced state.
- [x] Render server data with Django escaping. Link records/invoices to existing authorized detail pages in a new tab so the planner stays in place.
- [x] Add default-off switch and billing filter to existing planner form. No existing action icon sizes, card spacing or shared CSS changes.

### 4. Verification and local handoff

- [x] Run all Django tests with fast test hasher and filesystem test storage; run all existing JS tests plus new tests.
- [x] Run migration consistency and diff-whitespace checks.
- [x] Review spec compliance, then code quality, address findings and re-test.
- [x] Start local Django preview against a disposable demonstration database, not a production DB; verify desktop/mobile views and drawer via browser.
- [x] Report tested scope and preview URL. No push or Main merge without subsequent user direction.

## Baseline

`origin/main` at `1417d004ff4411b699fda81b4c33dccb97eafb47`.
109 existing scheduling/cancellation tests pass before edits.
Existing unrelated documentation/prototype changes are preserved and excluded.

## Verification Record

- Full Django suite: 879 tests, OK with 2 PostgreSQL-only locking tests skipped on SQLite.
- JS suite: 49 passed, including 8 new drawer lifecycle/form tests.
- Feature Django tests: 27 data projection + 13 view/permission/template tests.
- No migrations detected; diff whitespace check passes.
- Spec review findings fixed with red/green regressions: competing cancellation/log records require review; billing filtering preserves worker conflict warnings; rostered breaks remain visible without a log.
- Independent code-quality review: no actionable findings; 164 focused Django and 8 feature JS tests passed independently.
- Browser: daily, participant, worker views; on/off and Ready filter; issued/ready/cancellation drawers; +15/-15 minute examples; Escape focus return; desktop 1392x900 and mobile 390x844 without drawer horizontal overflow; no console warnings/errors.
- Local preview uses a separate disposable database with 11 demonstration shifts. No live data, pushes or merges.
- Preview: http://127.0.0.1:8006/roster/planner/?view=daily&date_from=2026-09-28&date_to=2026-10-04&billing=1
