# Phase 22 UI Consistency Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve table, action, and page-header consistency without changing business behavior.

**Architecture:** Keep styling centralized in `static/css/app.css`. Avoid page-specific template churn unless CSS cannot resolve an inconsistency.

**Tech Stack:** Django templates, plain CSS.

---

### Task 1: CSS Polish

**Files:**
- Modify: `static/css/app.css`

- [ ] Tighten page-header wrapping and action alignment.
- [ ] Override table-card behavior so it does not inherit awkward grid/card spacing.
- [ ] Style `td.actions a` as compact action links.
- [ ] Improve table row border consistency and empty-state spacing.

### Task 2: Verify

**Files:**
- No expected app code changes.

- [ ] Run `python manage.py check`.
- [ ] Inspect the changed CSS diff.
- [ ] Run browser smoke checks if local server is available.
