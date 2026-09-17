# Support Worker Desktop Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give non-document Support Worker pages a consistent large-screen workspace without changing mobile presentation or business logic.

**Architecture:** Add one presentational class to the outer sections of non-document worker templates. Add desktop-only CSS in the portal stylesheet so existing mobile selectors and all document templates remain untouched.

**Tech Stack:** Django templates, CSS, Django TestCase

---

### Task 1: Lock the desktop layout contract with tests

**Files:**
- Modify: `core/tests_dashboards.py`

- [x] Add a test that reads the relevant templates and requires `worker-desktop-page` on all non-document worker pages.
- [x] In the same test, require document templates to remain free of the new class.
- [x] Add a CSS contract test for `@media (min-width: 981px)`, the desktop hook, and the 1180px workspace.
- [x] Run the new tests and confirm they fail because the hooks and CSS do not exist yet.

### Task 2: Add page-level desktop hooks

**Files:**
- Modify: `templates/core/worker_dashboard.html`
- Modify: `templates/core/worker_placeholder.html`
- Modify: `templates/scheduling/worker_shift_list.html`
- Modify: `templates/scheduling/worker_shift_detail.html`
- Modify: `templates/service_logs/worker_log_list.html`
- Modify: `templates/service_logs/worker_service_log_detail.html`
- Modify: `templates/service_logs/worker_service_log_form.html`
- Modify: `templates/workers/worker_profile.html`

- [x] Add `worker-desktop-page` to each non-document outer section.
- [x] Add focused modifier classes where profile and service-log pages have multiple sections.
- [x] Do not alter template conditions, links, forms, field rendering, or document templates.

### Task 3: Implement desktop-only presentation

**Files:**
- Modify: `static/css/portal.css`

- [x] Add an `@media (min-width: 981px)` block.
- [x] Stretch `.worker-desktop-page` to `min(100%, 1180px)` and center it in the main workspace.
- [x] Normalize desktop card spacing and padding.
- [x] Use three equal columns for the My Shifts summary and keep filters comfortably aligned.
- [x] Keep detail-list labels at a readable fixed desktop width.
- [x] Run the new contract tests and confirm they pass.

### Task 4: Verify behavior and responsive boundaries

**Files:**
- Test: `core/tests_dashboards.py`
- Test: `scheduling/tests_shifts.py`
- Test: `service_logs/tests_service_logs.py`
- Test: `workers/tests.py`

- [x] Run focused Dashboard, Shifts, Logs, and Profile tests.
- [x] Run `python manage.py check`.
- [x] Run `git diff --check`.
- [x] Inspect desktop and mobile screenshots, confirming Documents and widths at 980px and below are unchanged.
