# Phase 55B Service Logs Table Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Service Logs list table density without changing behavior.

**Architecture:** Scope all markup and CSS changes to the Service Logs list. Add table/cell classes and CSS rules for width, wrapping, and compact column sizing while preserving links, form names, URLs, sorting, and invoice actions.

**Tech Stack:** Django templates, CSS, Django TestCase.

---

### Task 1: Table Structure Regression Test

**Files:**
- Modify: `service_logs/tests_review.py`

- [x] Add a test that verifies the Service Logs list renders `service-log-table` and `notes-cell`.
- [x] Include checks that existing bulk invoice checkbox and invoice shortcut remain present for approved logs.

### Task 2: Template Classes

**Files:**
- Modify: `templates/service_logs/service_log_list.html`

- [x] Add `class="service-log-table"` to the Service Logs table.
- [x] Add `class="notes-cell"` to the notes table cell.
- [x] Preserve all existing URLs, field names, sorting links, checkbox names, and action labels.

### Task 3: Scoped CSS

**Files:**
- Modify: `static/css/app.css`

- [x] Add scoped `.service-log-table` rules to tighten narrow columns.
- [x] Add `.service-log-table .notes-cell` wrapping and width rules.
- [x] Avoid changing global table behavior.

### Task 4: Verification

- [x] Run `python manage.py check`.
- [x] Run the focused Service Logs table test.
- [x] Run Service Logs and invoice shortcut tests.
- [x] Browser-check `/service-logs/`.
- [ ] Commit and push the branch.
