# Phase 49 Create Return State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve filtered list context when creating Participants, Support Workers, and Roster shifts.

**Architecture:** Reuse the existing `next` query parameter, `get_safe_return_url`, and form `return_url` hidden field pattern. Create views redirect to the safe return URL only when one is supplied; otherwise they keep the existing detail redirect behavior.

**Tech Stack:** Django views, Django templates, Django TestCase.

---

### Task 1: Participant Create Return State

**Files:**
- Modify: `participants/tests.py`
- Modify: `participants/views.py`
- Modify: `templates/participants/participant_list.html`

- [ ] Write a failing test proving Add Participant carries `next`, the create form Cancel link uses it, and save redirects to it.
- [ ] Run the focused participant test and confirm it fails because create return state is missing.
- [ ] Add safe return handling to `participant_create`.
- [ ] Update Participant list Add links to carry `next`.
- [ ] Re-run the focused participant test and confirm it passes.

### Task 2: Worker Create Return State

**Files:**
- Modify: `workers/tests.py`
- Modify: `workers/views.py`
- Modify: `templates/workers/worker_list.html`

- [ ] Write a failing test proving Add Worker carries `next`, the create form Cancel link uses it, and save redirects to it.
- [ ] Run the focused worker test and confirm it fails because create return state is missing.
- [ ] Add safe return handling to `worker_create`.
- [ ] Update Worker list Add links to carry `next`.
- [ ] Re-run the focused worker test and confirm it passes.

### Task 3: Roster Create Return State

**Files:**
- Modify: `scheduling/tests_shifts.py`
- Modify: `scheduling/views.py`
- Modify: `templates/scheduling/roster_list.html`

- [ ] Write a failing test proving New Shift carries `next`, the create form Cancel link uses it, and save redirects to it.
- [ ] Run the focused shift test and confirm it fails because create return state is missing.
- [ ] Add safe return handling to `shift_create`.
- [ ] Update Roster New Shift links to carry `next`.
- [ ] Re-run the focused shift test and confirm it passes.

### Task 4: Verification

- [ ] Run focused tests for the three new create return behaviors.
- [ ] Run `python manage.py test participants workers scheduling`.
- [ ] Run `python manage.py check`.
- [ ] Run full `python manage.py test`.
- [ ] Review diff scope, commit, and push the Phase 49 branch.
