# Phase 51 Status Pill Colors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semantic status colors across admin status pills.

**Architecture:** Keep the existing `status-pill` base class and add status-specific modifier classes in templates. Extend CSS with shared status color mappings.

**Tech Stack:** Django templates, Django TestCase, CSS.

---

### Task 1: Add Status Class Tests

**Files:**
- Modify: `participants/tests.py`
- Modify: `workers/tests.py`
- Modify: `scheduling/tests_shifts.py`
- Modify: `service_logs/tests_review.py`
- Modify: `invoices/tests_invoices.py`

- [ ] Add tests proving representative list pages render `status-<value>` classes.
- [ ] Run focused tests and confirm they fail before template changes.

### Task 2: Add Status Classes to Templates

**Files:**
- Modify admin list and detail templates that render `status-pill`.

- [ ] Add `status-{{ object.status }}` or equivalent classes to Participants, Workers, Roster, Service Logs, Invoices, and Support Items.
- [ ] Preserve existing text and links.
- [ ] Re-run focused tests and confirm they pass.

### Task 3: Add Semantic CSS Colors

**Files:**
- Modify: `static/css/app.css`

- [ ] Extend `.status-pill.status-*` rules for common statuses.
- [ ] Keep existing worker shift colors compatible.
- [ ] Run app checks and related tests.

### Task 4: Verification

- [ ] Run `python manage.py check`.
- [ ] Run focused app tests.
- [ ] Run full `python manage.py test`.
- [ ] Review diff scope, commit, and push the Phase 51 branch.
