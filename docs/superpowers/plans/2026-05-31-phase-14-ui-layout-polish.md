# Phase 14 UI Layout Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the local V1 admin and worker UI presentation without changing business logic, permissions, models, or database structure.

**Architecture:** Keep changes in shared templates and the existing stylesheet. Use current Django template patterns and existing URL names. Validate with template-focused tests, Django system check, and browser checks.

**Tech Stack:** Django templates, CSS, Django test runner, local in-app browser.

---

### Task 1: Base Layout And Navigation Polish

**Files:**
- Modify: `static/css/app.css`
- Modify: `templates/admin_base.html`
- Modify: `templates/worker_base.html`

- [ ] **Step 1: Add semantic nav wrappers and current-user labels**

Update base templates so CSS can target navigation groups and user areas without changing URL behavior:

```django
<nav class="sidebar-nav" aria-label="Admin navigation">
```

```django
<nav class="bottom-nav" aria-label="Worker navigation">
```

- [ ] **Step 2: Improve shared layout CSS**

Update `static/css/app.css` to improve shell spacing, typography, nav link display, cards, tables, forms, and mobile behavior. Keep all class names compatible with existing templates.

- [ ] **Step 3: Run template checks**

Run: `python manage.py check`

Expected: `System check identified no issues`.

### Task 2: Dashboard Presentation Polish

**Files:**
- Modify: `templates/core/admin_dashboard.html`
- Modify: `templates/core/worker_dashboard.html`
- Modify: `static/css/app.css`
- Test: `core/tests_dashboards.py`

- [ ] **Step 1: Add dashboard intro wrappers**

Wrap dashboard headings in `page-header` blocks where needed. Keep all links and URL names the same.

- [ ] **Step 2: Make dashboard links look like action buttons**

Use existing `.button` styles or a card action style in CSS. Do not add business logic.

- [ ] **Step 3: Run dashboard tests**

Run: `python manage.py test core.tests_dashboards`

Expected: 2 tests pass.

### Task 3: Verification And Browser Review

**Files:**
- No code files unless a rendering issue is found.

- [ ] **Step 1: Run full relevant tests**

Run: `python manage.py test accounts core documents invoices participants scheduling service_logs workers -v 1`

Expected: 106 tests pass.

- [ ] **Step 2: Browser-check admin dashboard**

Open `http://127.0.0.1:8000/admin-dashboard/`, log in as admin if needed, and confirm the dashboard renders with updated cards.

- [ ] **Step 3: Browser-check worker dashboard**

Open `http://127.0.0.1:8000/sw/dashboard/`, log in as worker if needed, and confirm the dashboard renders with updated cards and bottom nav.

- [ ] **Step 4: Commit and push**

Commit message:

```bash
git commit -m "style: polish v1 layout"
```
