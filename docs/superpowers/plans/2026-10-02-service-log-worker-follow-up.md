# Service Log Worker Filters and Follow-Up

> Execution: implement inline with tests first; preserve the current staging workflow.

**Goal:** Apply the accepted HTML preview to the Admin Service Logs page without
changing submission, approval, cancellation review, or invoice creation.

**Architecture:** Extend the list view's existing GET filters with a worker ID.
Apply the same participant, worker, and service-date scope to normal logs,
approved uninvoiced cancellation charges, and a separate read-only missing-log
query. Render missing shifts in native, initially collapsed details elements.

**Stack:** Django ORM/templates, Admin-scoped CSS, small progressive-enhancement
JavaScript for date inputs. No schema changes, scheduled jobs, or notifications.

## Accepted Rules

- Keep all existing statuses and default date scope. Include inactive workers in
  historical filtering, just as participants remain available for history.
- Preserve worker filters through status changes, sorting, pagination, and detail
  return URLs. Clear keeps only the current status, matching existing behavior.
- Missing logs are scheduled Published/Confirmed shifts whose rostered end has
  passed in the business timezone, with no service log. Exclude pending,
  approved, and waived cancellation reports; rejected reports do not exclude
  restored shifts. Exclude drafts, no-shows, completed/cancelled shifts, future
  or in-progress shifts, and unscheduled services.
- Log status does not constrain the missing-log query. Its counts use the whole
  participant/worker/date scope, independently of the main table's pagination.
- Group missing shifts by worker, then earliest service date and start time.
  Link to the existing read-only shift detail. Never add billing checkboxes or
  change the database from a GET request.
- Keep the unified Approved billing table and its separate log/cancellation IDs.
- Preserve default global status-card counts. Filtered totals remain scoped.

## Tasks

- [x] Verify baseline appearance and date-filter tests (40 passed).
- [x] Add failing worker-filter, missing-log, scope, timezone, and read-only tests
  in `service_logs/tests_follow_up.py` using an isolated database.
- [x] Add a focused `service_logs/follow_up.py` query/grouping helper and wire it
  into `service_logs/views.py`; add worker filtering to both billing sources.
- [x] Update `templates/service_logs/service_log_list.html` and add the missing
  summary partial. Scope styling in `static/css/admin.css` to this page so SC
  filters and worker pages are unaffected. Use native details for disclosure.
- [x] Add page-specific date-input enhancement so manually entered dates select
  Custom; reject a reversed range in the browser without changing the server's
  existing tolerant date resolver.
- [x] Run follow-up, service-log review/submission, cancellation, invoice,
  pagination/sorting, and appearance regressions. Verify actual rendered Django
  HTML with browser interactions at desktop and mobile widths.
- [x] Check for migrations and unrelated changes and review the diff.

Delivery: push the scoped branch and create a PR targeting staging. Do not merge
staging or main; deployment acceptance remains a separate step.

## Verification

`python manage.py test service_logs.tests_follow_up` must first fail on the absent
worker filter/missing summary, then pass after implementation. Expanded regression:
`python manage.py test service_logs scheduling invoices core.tests_theme
core.tests_admin_appearance`. Use only a local ephemeral SQLite test database;
test-only fast password hashing is allowed and must not change runtime settings.

Browser checks cover preserved GET controls, native disclosure, links, date
editing, filtering, no page overflow at 320/390/760/1280/1512px, and cancellation
rows remaining selectable only through the existing invoice form. No production
or staging data is created by verification.

## Results

- New regression tests failed before implementation and passed afterward (14).
- Expanded regression suite passed: 389 tests, in-memory SQLite with a test-only
  fast password hasher. No model changes or migrations detected; Django checks
  and whitespace checks passed.
- Actual Django pages verified with Playwright/Chrome using an isolated local
  SQLite database: combined filters, status/sort preservation, date validation,
  preset dates, clear behavior, per-worker disclosure, shift detail navigation,
  mixed normal/cancellation invoice handoff, empty state, pagination, and menu.
- No page overflow at 320, 390, 760, 960, 1280, or 1512px. Desktop and mobile
  screenshots inspected. No JavaScript errors observed.
- Independent Python code review found no actionable issues. Historical missing
  shifts are loaded for the chosen scope; very large backlogs have not been load
  tested. PostgreSQL and physical iPhone Safari acceptance remain for staging.
