# Phase 52D Form and Detail Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish admin forms and detail pages without changing behavior.

**Architecture:** Keep existing templates and class names. Refine CSS rules for record forms, form sections, fields, actions, detail lists, workflow panels, and inline forms.

**Tech Stack:** CSS and Django TestCase.

---

### Task 1: Form Structure Regression Test

**Files:**
- Modify: `participants/tests.py`

- [x] Add a lightweight assertion that the participant create page renders existing `form-section` structure.
- [x] Run the focused test.

### Task 2: Form and Detail CSS Polish

**Files:**
- Modify: `static/css/app.css`

- [x] Refine form section spacing, headings, field labels, form actions, detail lists, workflow panels, and inline forms.
- [x] Preserve existing selectors, form fields, and submit behavior.

### Task 3: Verification

- [x] Run `python manage.py check`.
- [x] Run representative form/detail app tests.
- [x] Run full `python manage.py test`.
- [ ] Commit and push the branch.
