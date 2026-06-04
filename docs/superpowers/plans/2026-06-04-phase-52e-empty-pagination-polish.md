# Phase 52E Empty State and Pagination Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish empty states, pagination, and zero-state summary panels without changing business behavior.

**Architecture:** Keep existing list templates and pagination behavior. Add a small empty-state action wrapper for stable styling, then refine shared CSS selectors for empty states, pagination, and dashboard zero-state panels.

**Tech Stack:** Django templates, CSS, Django TestCase.

---

### Task 1: Empty State Structure Test

**Files:**
- Modify: `participants/tests.py`

- [x] Add a failing test proving the participant list empty state renders an `empty-state-actions` wrapper around its action link.
- [x] Run the focused test and confirm it fails before implementation.

### Task 2: Template Structure

**Files:**
- Modify: `templates/participants/participant_list.html`
- Modify: `templates/workers/worker_list.html`
- Modify: `templates/scheduling/roster_list.html`
- Modify: `templates/scheduling/support_item_list.html`
- Modify: `templates/service_logs/service_log_list.html`
- Modify: `templates/invoices/invoice_list.html`
- Modify: `templates/documents/document_list.html`

- [x] Wrap empty-state action links in `<div class="empty-state-actions">`.
- [x] Preserve all existing links, labels, URL names, and query parameters.

### Task 3: CSS Polish

**Files:**
- Modify: `static/css/app.css`

- [x] Refine `.empty-state`, `.empty-state-actions`, `.summary-empty-state`, `.pagination`, and `.pagination-links`.
- [x] Preserve existing responsive behavior and avoid layout shifts.

### Task 4: Verification

- [x] Run `python manage.py check`.
- [x] Run the focused empty-state test.
- [x] Run representative list/pagination app tests.
- [x] Run full `python manage.py test`.
- [ ] Commit and push the branch.
