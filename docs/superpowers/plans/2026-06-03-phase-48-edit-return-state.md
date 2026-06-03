# Phase 48 Edit Return State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve list return state when editing Participants, Support Workers, and Roster shifts.

**Architecture:** Reuse the existing `next` and `get_safe_return_url` pattern introduced in Phase 47. Carry the safe return URL through GET, form POST, cancel links, and successful save redirects.

**Tech Stack:** Django views, Django templates, Django TestCase.

---

### Task 1: Participant Edit Return State

**Files:**
- Modify: `participants/tests.py`
- Modify: `participants/views.py`
- Modify: `templates/participants/participant_list.html`
- Modify: `templates/participants/participant_form.html`

- [ ] Write a failing test proving the filtered Participants list `Edit` link carries `next`, the edit form cancel link uses it, and save redirects to it.
- [ ] Run the focused participant test and confirm it fails because the behavior is missing.
- [ ] Add safe return context and POST handling to `participant_edit`.
- [ ] Update participant list and form templates.
- [ ] Re-run the focused participant test and confirm it passes.

### Task 2: Worker Edit Return State

**Files:**
- Modify: `workers/tests.py`
- Modify: `workers/views.py`
- Modify: `templates/workers/worker_list.html`
- Modify: `templates/workers/worker_form.html`

- [ ] Write a failing test proving the filtered Support Workers list `Edit` link carries `next`, the edit form cancel link uses it, and save redirects to it.
- [ ] Run the focused worker test and confirm it fails because the behavior is missing.
- [ ] Add safe return context and POST handling to `worker_edit`.
- [ ] Update worker list and form templates.
- [ ] Re-run the focused worker test and confirm it passes.

### Task 3: Roster Edit Return State

**Files:**
- Modify: `scheduling/tests_shifts.py`
- Modify: `scheduling/views.py`
- Modify: `templates/scheduling/roster_list.html`
- Modify: `templates/scheduling/shift_form.html`

- [ ] Write a failing test proving the filtered Roster list `Edit` link carries `next`, the shift edit form cancel link uses it, and save redirects to it.
- [ ] Run the focused roster test and confirm it fails because the behavior is missing.
- [ ] Add safe return context and POST handling to `shift_edit`.
- [ ] Update roster list and shift form templates.
- [ ] Re-run the focused roster test and confirm it passes.

### Task 4: Verification

**Files:**
- Verify all touched apps.

- [ ] Run `python manage.py test participants workers scheduling`.
- [ ] Run `python manage.py check`.
- [ ] Run full `python manage.py test`.
- [ ] Review diff scope, commit, and push the Phase 48 branch.
