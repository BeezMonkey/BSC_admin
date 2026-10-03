# SC Log Revisions Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task. Steps use checkboxes for progress.

**Goal:** Enable safe SC revisions and Admin correction records without changing SW behavior.

**Architecture:** SC-only edit form and transactional revision/review helpers. A related
history model stores snapshots; signed timestamp tokens reject stale edits/reviews.
Invoice creation revalidates locked logs before persisting snapshots.

**Tech Stack:** Django, existing templates/CSS/date picker, PostgreSQL production,
isolated SQLite tests, Playwright local UI verification.

## Task 1: Guarded revisions and review

Files: coordinators/models.py, forms.py, log_revisions.py, views.py, urls.py,
tests_revisions.py, migrations; core/models.py and audit choice migration.

- [x] Read current ownership, form validation, invoice association, and review paths.
- [x] Run baseline: Python bsc-follow-up-tests.py coordinators invoices (173 passed).
- [x] Write tests using `/sc/logs/<id>/edit/`, mandatory `revision_token`,
  `revision_reason`, and existing form fields; expect unchanged ID, submitted status,
  cleared review fields, one history snapshot with original notes and review.
- [x] Verify new edit requests fail with 404 before implementing the route.
- [x] Implement `CoordinationLogChange` (revision/review/correction types, JSON
  before/after, actor/time/reason), `revision_token(log)`, and `record_log_change`.
- [x] Implement locked edit and review paths; reject stale/missing tokens, invoice
  links, changed participant, unchanged content. Add Admin correction append path.
- [x] Verify permission, state, audit rollback, history and invoice lock tests.

## Task 2: Invoice race protection

Files: invoices/views.py and focused invoice revision tests.

- [x] Reproduce an approved log changing after initial selection using a controlled
  test hook; assert no invoice is created for stale data.
- [x] In transaction, lock candidate logs ordered by primary key, compare timestamps,
  recheck approved/unlinked status, participant and period; abort whole invoice if
  any selected record changed. Keep service invoice path unchanged.
- [x] Run invoices and coordinator regression tests.

## Task 3: Portal and Admin UI

Files: SC list/detail/form templates, Admin detail, shared SC history partial,
SC correction template, scoped static CSS/JS if needed, coordinators/admin.py.

- [x] Test eligible Edit links, invoiced read-only, review tokens and history markup.
- [x] Reuse existing forms and layouts. Add reason and before/after history. Add
  Admin-only correction form (text correction or invoice-review-required note).
- [x] Make Django coordination log/history administration read-only to avoid bypass.
- [x] Verify desktop/mobile form, validation, edit-resubmit-review and corrections.

## Task 4: Verification

- [x] Check migrations using `makemigrations --check --dry-run` and Django check.
- [x] Run complete relevant regression suites, including SW/service logs.
- [x] Independent review and repair actionable findings; rerun affected tests.
- [x] `git diff --check`, verify only intended files and no production/test data.
- [x] Report local result and deployment state. Do not merge or deploy without a
  follow-up request; offer staging PR as the next step.

## Deployment and Manual Acceptance

Two additive migrations create the change-history table and extend audit choices.
Before serving this version, the existing Render pre-deploy step must run
`python manage.py migrate` (build.sh only collects static assets).

On isolated staging demo data:
1. Edit an SC-owned approved log. Confirm the same ID is now Submitted and absent
   from billable selections until approved again.
2. Reopen a pre-edit Admin tab and try to approve. Confirm it refuses stale review.
3. Create an SC draft invoice. Confirm SC edit is locked, including direct POST.
4. Append an Admin correction. Confirm history is added but invoice values do not change.
5. Cancel/delete a draft through existing actions. Confirm released logs can be revised
   and that revisions still require approval before another invoice.

SQLite verifies state interleavings and rollback, not real database row contention.
The PostgreSQL-only contention regression must be run on a disposable PostgreSQL
test database before claiming that platform's concurrent behavior verified. Never
point the test runner at a production data store.

## Verified Result (2026-10-03)

- Complete suite: 723 tests, 722 passed and one PostgreSQL-only test skipped on SQLite.
- Django check, migration drift check and whitespace check passed.
- Playwright verified edit/resubmit/approval, invoice lock, Admin correction, mobile
  hamburger, and no page overflow at 1440/960/760/390/320 pixels.
- Independent spec and code review completed. Fixed audit-summary privacy and
  concurrent invoice release findings, then reran tests.
- Local branch only; no GitHub push, deployment, merge, or production data access.
