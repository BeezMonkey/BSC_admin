# Phase 26 Workflow Readiness Panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight readiness and next-step panels to key operational detail pages.

**Architecture:** Use existing Django views to compute read-only readiness context. Render new cards in existing templates and style them through shared CSS.

**Tech Stack:** Django views, Django templates, plain CSS, Django TestCase.

---

### Task 1: Participant Readiness

**Files:**
- Modify: `participants/views.py`
- Modify: `templates/participants/participant_detail.html`
- Modify: `participants/tests.py`

- [x] Add readiness context for NDIS number, plan dates, and active assignment.
- [x] Render readiness and next-step cards.
- [x] Test readiness text and shortcuts.

### Task 2: Worker Readiness

**Files:**
- Modify: `workers/views.py`
- Modify: `templates/workers/worker_detail.html`
- Modify: `workers/tests.py`

- [x] Add readiness context for active status, compliance, and active assignment.
- [x] Render readiness and next-step cards.
- [x] Test readiness text and shortcuts.

### Task 3: Shift Workflow Status

**Files:**
- Modify: `scheduling/views.py`
- Modify: `templates/scheduling/shift_detail.html`
- Modify: `scheduling/tests_shifts.py`

- [x] Add workflow status text for shift states.
- [x] Render workflow status and action cards.
- [x] Test draft shift next-step guidance.

### Task 4: Shortcut Prefill

**Files:**
- Modify: `scheduling/views.py`
- Modify: `documents/views.py`
- Modify: `scheduling/tests_shifts.py`
- Modify: `documents/tests_documents.py`

- [x] Prefill shift participant and worker from query parameters.
- [x] Prefill document linked records from query parameters.
- [x] Test selected form values.

### Task 5: Verify

- [x] Run focused tests.
- [x] Run full test suite.
- [x] Review diff.
