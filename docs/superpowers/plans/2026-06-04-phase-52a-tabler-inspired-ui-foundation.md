# Phase 52A Tabler-Inspired UI Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the admin UI foundation with Tabler-inspired visual choices while preserving existing functionality.

**Architecture:** Keep existing Django templates and CSS architecture. Add minimal navigation classes in `admin_base.html`, and apply visual refinements in `static/css/app.css`.

**Tech Stack:** Django templates, Django TestCase, CSS.

---

### Task 1: Active Sidebar Navigation

**Files:**
- Modify: `core/tests_dashboards.py`
- Modify: `templates/admin_base.html`
- Modify: `static/css/app.css`

- [ ] Add a failing test proving the dashboard sidebar link renders with `sidebar-link active`.
- [ ] Update `admin_base.html` to add `sidebar-link` and route-aware `active` classes.
- [ ] Add active sidebar styling in CSS.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: Safe Foundation Polish

**Files:**
- Modify: `static/css/app.css`

- [ ] Update font stack, colors, card shadow, button sizing, table header, table hover, form controls, and content spacing.
- [ ] Keep all existing class names and behavior.
- [ ] Do not import or copy Tabler source.

### Task 3: Verification

- [ ] Run `python manage.py check`.
- [ ] Run focused dashboard tests.
- [ ] Run relevant app tests.
- [ ] Run full `python manage.py test`.
- [ ] Review diff scope and ensure `reference_templates/` is not staged.
- [ ] Commit and push the Phase 52A branch.
