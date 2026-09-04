# Unscheduled Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add worker-submitted Unscheduled Service logs that appear in admin roster, service logs, PDFs, and invoice flow.

**Architecture:** Keep `ServiceLog.shift` required by creating a completed backing `Shift` for each unscheduled submission. Mark both the shift and service log source so admin surfaces and PDFs can distinguish scheduled vs unscheduled records.

**Tech Stack:** Django models, forms, views, templates, migrations, and Django TestCase tests.

---

### Task 1: Model And Form Contract

**Files:**
- Modify: `scheduling/models.py`
- Modify: `service_logs/models.py`
- Modify: `service_logs/forms.py`
- Create: model migrations
- Test: `service_logs/tests_service_logs.py`

- [ ] Add failing tests that an unscheduled form requires participant, date, support item, and reason, and that submission stores `source=unscheduled`.
- [ ] Add `Shift.Source` with `SCHEDULED` and `UNSCHEDULED` values, defaulting existing shifts to scheduled.
- [ ] Add `ServiceLog.Source` and `unscheduled_reason`, defaulting existing logs to scheduled and blank reason.
- [ ] Add an unscheduled form that extends the existing service log fields with participant, service date, support item, and reason.

### Task 2: Worker Submission Flow

**Files:**
- Modify: `service_logs/views.py`
- Modify: `service_logs/urls.py`
- Modify: `templates/service_logs/worker_service_log_form.html`
- Modify: `templates/core/worker_dashboard.html`
- Modify: `templates/service_logs/worker_log_list.html`
- Test: `service_logs/tests_service_logs.py`

- [ ] Add failing tests for worker access to `worker_unscheduled_service_log_create`, assigned participant filtering, and successful POST creation.
- [ ] Implement the worker view to validate assigned participants, create a completed backing shift, create a submitted service log, store attachments transactionally, notify admin, and show a success message.
- [ ] Reuse the existing attachment picker and allow the template to render with or without a pre-existing shift.
- [ ] Add `Submit Unscheduled Service` entry points on Home and My Logs.

### Task 3: Admin Visibility And PDF

**Files:**
- Modify: `templates/service_logs/service_log_detail.html`
- Modify: `templates/service_logs/service_log_list.html`
- Modify: `templates/scheduling/roster_list.html`
- Modify: `templates/scheduling/roster_planner.html`
- Modify: `service_logs/views.py`
- Test: `service_logs/tests_review.py`
- Test: `scheduling/tests_shifts.py`

- [ ] Add failing tests that admin detail, list, roster, and PDF expose the unscheduled marker and reason.
- [ ] Display `Unscheduled` markers without changing existing scheduled records.
- [ ] Add `Service type: Unscheduled` and `Reason` to the service log PDF.

### Task 4: Verification

**Files:**
- Test: relevant Django suites

- [ ] Run `python manage.py makemigrations --check --dry-run` after committing migrations to confirm no missing migrations.
- [ ] Run targeted service log, scheduling, dashboard, and theme tests.
- [ ] Run `python manage.py check`.
- [ ] Run `git diff --check`.

