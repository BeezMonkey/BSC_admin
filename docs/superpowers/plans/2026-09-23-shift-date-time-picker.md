# Shift Date and Time Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace native date and time controls on Admin New/Edit Shift forms with the approved compact calendar and five-minute wheel pickers without changing scheduling business logic.

**Architecture:** Keep Django's existing field names and submitted ISO values in hidden inputs, and render a shared presentation partial around them. A standalone JavaScript module initializes both full-page forms and AJAX-inserted Planner modals; global scoped CSS provides the approved desktop and mobile layout.

**Tech Stack:** Django templates and tests, vanilla JavaScript, existing `static/css/app.css` design tokens.

---

### Task 1: Lock the template contract

**Files:**
- Modify: `scheduling/tests_shifts.py`

- [x] Add response assertions for date/time picker hooks, hidden ISO fields, helper copy, and static asset loading.
- [x] Run the focused tests and confirm they fail because the custom picker markup is absent.

### Task 2: Render the approved controls

**Files:**
- Create: `templates/scheduling/partials/date_time_picker_field.html`
- Modify: `templates/scheduling/partials/shift_form_fields.html`
- Modify: `templates/scheduling/shift_form.html`
- Modify: `templates/scheduling/roster_planner.html`
- Modify: `static/js/shift_modal.js`

- [x] Preserve `service_date`, `start_time`, and `end_time` as hidden Django inputs.
- [x] Render the compact calendar and three-column hour/minute/period wheel markup.
- [x] Load the picker asset on full forms and Planner pages, and initialize newly inserted modal content.

### Task 3: Add scoped interaction and styling

**Files:**
- Create: `static/js/date_time_picker.js`
- Modify: `static/css/app.css`

- [x] Implement calendar navigation, weekend emphasis, Today/Clear, ISO date submission, and responsive placement.
- [x] Implement compact hour, five-minute, and AM/PM wheels with draft state, Cancel, OK, snapping, and `HH:MM` submission.
- [x] Preserve keyboard focus, Escape/outside-click dismissal, and visible focus styles.

### Task 4: Verify and publish

**Files:**
- Modify: `scheduling/tests_shifts.py`

- [x] Run focused Shift tests, Django system checks, JavaScript syntax checks, and `git diff --check`.
- [x] Visually inspect full-page and Planner modal pickers at desktop and mobile widths.
- [x] Commit, push `codex/date-time-picker`, create a GitHub PR, and attach it to the task.
