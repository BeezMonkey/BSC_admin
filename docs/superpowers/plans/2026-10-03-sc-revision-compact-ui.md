# Compact SC Revision UI Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development and test-driven-development for these scoped presentation tasks.

**Goal:** Make revision entry and history compact while retaining full audit content and all workflow guards.

**Architecture:** Keep existing forms/views/storage. Native details elements progressively reveal optional revision text and secondary history metadata. Derived model properties group the existing display diff; scoped JavaScript only controls text visibility. Dedicated CSS does not affect SW or unrelated pages.

**Tech Stack:** Django, semantic HTML tables/disclosures, scoped CSS and JavaScript, Django tests and browser checks.

## Task 1: Revision Form (Delegated)

- [x] Add failing UI tests in `coordinators/tests_revision_form_ui.py`: optional disclosure collapsed on GET; Other, retained details and errors expanded; new-log form unaffected.
- [x] Update `templates/coordinators/sc_coordination_log_form.html`, `static/js/sc_log_revision.js`, and a scoped `static/css/sc_log_revision.css`. Reason select is at most 28rem wide, optional Add details disclosure opens automatically for Other. Reason changes never discard text; no-JS still allows access. No forms/views/permissions modifications. Other hides the redundant disclosure summary, leaving the required field label visible.
- [x] Verify form tests and spec review. Form/revision tests: 43 passed; nine JavaScript smoke checks passed.

## Task 2: History Presentation

- [x] Add failing tests in `coordinators/tests_history_ui.py` for business/review grouping, compact summary, unchanged snapshots, complete escaped text, approval/correction-only entries, and collapsed review details.
- [x] Extend existing `CoordinationLogChange.field_changes` display data with field keys and derived `content_changes`, `review_changes`, and `changed_fields_summary`; keep snapshot and storage behavior unchanged.
- [x] Replace repeated field blocks in `templates/coordinators/partials/log_history.html` with a single shared table header and secondary native review disclosure. Add reusable table/text partials.
- [x] Update `static/css/coordination_revisions.css` and add `static/js/sc_log_history.js`: 3-line previews with full-text buttons only when clipped, full text by default without JS, consistent responsive table stacking and keyboard operation.
- [x] Verify history tests and independent spec/code review. Both reviews completed cleanly after fixing the resize/full-text-toggle edge case and inherited table minimum width.

## Task 3: Integrated Preview

- [x] Run all revision/history and invoice regressions, complete isolated SQLite suite, Django check, migration dry run, and whitespace diff check. Final full suite: 745 passed, one PostgreSQL-only contention test skipped; no migration changes or check errors.
- [x] Preserve the user's local demo DB and sessions when restarting port 8004; do not recreate their current test records.
- [x] Verify desktop/mobile 1440/846/390/320 widths, optional/Other transitions, retained error content, long/short history, secondary audit expansion and no overflow. No deployed DB access, push, PR or merge. Verified actual Other validation failure retains input and does not write to the source record; long history before/after expand and collapse independently.
- [x] Open SC on 127.0.0.1 and Admin on localhost to retain independent login sessions, then hand over both preview links. Temporary browser viewport overrides reset and test tab closed.
