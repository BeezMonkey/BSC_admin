# Phase 52B Sidebar and Header Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the global sidebar and page header visuals without changing app behavior.

**Architecture:** Keep existing Django shell structure. Add small brand subtitle markup and refine existing CSS selectors.

**Tech Stack:** Django templates, CSS, Django TestCase.

---

### Task 1: Brand Markup

**Files:**
- Modify: `templates/admin_base.html`
- Modify: `core/tests_dashboards.py`

- [ ] Add a small brand subtitle under Brisbane Star Care.
- [ ] Add or update a test proving the shell still renders the brand and active link.

### Task 2: Sidebar and Header CSS

**Files:**
- Modify: `static/css/app.css`

- [ ] Make sidebar width, brand, nav item spacing, hover state, and active state more visually distinct.
- [ ] Add topbar and page header spacing polish.
- [ ] Keep class names and page structure intact.

### Task 3: Verification

- [ ] Run `python manage.py check`.
- [ ] Run `python manage.py test core accounts`.
- [ ] Run full `python manage.py test`.
- [ ] Confirm no reference template files are staged.
- [ ] Commit and push the branch.
