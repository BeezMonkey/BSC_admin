# Shared Date Picker Anchoring Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Keep the existing isolated worktree and validate each checkpoint.

**Goal:** Reuse SC's anchored calendar positioning for every existing shared date picker without changing time pickers, native inputs, validation, permissions, or billing.

**Architecture:** Move SC's viewport positioning into the shared date-picker lifecycle in `static/js/date_time_picker.js`. Only calendar instances use the new positioning and listeners; preserve all value-selection methods. Scope fixed-position CSS to date calendars. Remove the redundant SC-only script and positioning CSS, while preserving SC form appearance.

**Tech Stack:** Django templates, existing CSS, vanilla JavaScript, Node test runner, Django tests, browser verification.

## Task 1: Regression Tests

- [x] Replace the SC-only positioning fixture with a shared-picker DOM fixture in `tests/js/date_picker_position.test.cjs`.
- [x] Preserve coverage for a 6px anchor gap, upward placement, horizontal clamping, scroll tracking, fixed navigation, visual viewport, changing calendar height, hidden anchors and close cleanup.
- [x] Add coverage for dynamic modal initialization, modal scroll bounds, date selection/Clear/Today events, time-picker isolation and repeated initialization.
- [x] Update `coordinators/tests_duration.py` to require the shared script, reject the obsolete SC script, and preserve SC-only form appearance.
- [x] Run `node --test tests/js/date_picker_position.test.cjs` and focused Django tests; confirm expected failures before implementation.

## Task 2: Shared Placement

- [x] Add an explicit calendar-instance flag in `static/js/date_time_picker.js`.
- [x] Position calendars from trigger viewport coordinates with gap 6px and viewport margin 8px. Reserve fixed worker/admin headers and worker bottom navigation; constrain modal calendars to `.shift-modal-body` bounds.
- [x] Prefer below, flip above if it has more room, clamp width/height, and close through `closePicker()` if the trigger leaves the usable area.
- [x] Attach shared scroll/resize/visualViewport listeners once; observe only the active calendar; cancel pending frames and disconnect the observer on close.
- [x] Add date-only CSS after the existing small-screen rules in `static/css/app.css`. Leave the time picker rules unchanged.
- [x] Remove obsolete positioning from `static/css/sc_log_form.css`, `static/js/sc_date_picker.js`, and its script include in `templates/coordinators/sc_coordination_log_form.html`.
- [x] Run all JavaScript tests and relevant Django tests; verify no migrations or business code changes.

## Task 3: Browser Verification And Review

- [x] Rebuild local static assets and restart only the isolated demo server.
- [x] Verify SC, worker unscheduled service, standalone shift, recurring dates, and dynamically opened Planner shift modal using browser mobile emulation; also check modal placement at the normal desktop viewport.
- [x] Check scroll-following, upward placement, fixed navigation, holiday content, date selection, unchanged time controls, and modal close/reopen without submitting forms. Automated coverage additionally checks visual-viewport changes and month-height changes.
- [x] Perform independent diff review, add suggested lifecycle regression tests, and present local preview. Do not push or merge without a new user request.

**Verification:** All 25 JavaScript tests pass. Full Django suite: 815 passed, one PostgreSQL-only row-lock test skipped on SQLite (816 total). `git diff --check` passes. Browser checks measured a 6px gap for recurring, worker, SC, standalone shift and Planner-modal calendars. Modal scrolling and close/reopen were checked against the isolated local demo database. No forms were submitted.

**Remaining environment check:** Physical iPhone/Safari and the on-screen keyboard have not been tested; mobile checks used Chromium viewport emulation, with visual-viewport geometry covered by unit tests. No GitHub push or deployment has been made.
