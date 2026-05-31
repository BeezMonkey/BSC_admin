# Phase 15 Demo Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable local demo-data setup command and documentation for V1 trial use.

**Architecture:** Implement one Django management command under `core` so it can coordinate users and records across apps without changing model behavior. Keep the command idempotent by using stable usernames, NDIS numbers, support item numbers, and service dates. Verify with command tests and the existing Django test suite.

**Tech Stack:** Django management commands, Django ORM, Django TestCase, existing V1 models.

---

### Task 1: Demo Data Command Tests

**Files:**
- Create: `core/tests_seed_demo_data.py`

- [ ] **Step 1: Add tests for command creation and idempotency**

Create tests that call `call_command("seed_demo_data")`, then assert users, profiles, participant, support worker, assignment, support item, shift, service log, invoice, and invoice line exist.

- [ ] **Step 2: Run tests and confirm they fail before implementation**

Run: `python manage.py test core.tests_seed_demo_data`

Expected: fails with an unknown command error before the command exists.

### Task 2: Management Command

**Files:**
- Create: `core/management/__init__.py`
- Create: `core/management/commands/__init__.py`
- Create: `core/management/commands/seed_demo_data.py`

- [ ] **Step 1: Create command package structure**

Add the Django management package folders under `core`.

- [ ] **Step 2: Implement `seed_demo_data`**

The command should:

- Create or update `admin`, `worker`, and `accountant`.
- Create or update role `UserProfile` records.
- Create or update one participant using NDIS number `430000001`.
- Create or update one support worker linked to `worker`.
- Create or update one active assignment.
- Create or update one support item using item number `01_011_0107_1_1`.
- Create or update one completed shift for `2026-06-01`.
- Create or update one approved service log for that shift.
- Create or reuse one invoice for June 2026 and one invoice line.

- [ ] **Step 3: Run command tests**

Run: `python manage.py test core.tests_seed_demo_data`

Expected: tests pass.

### Task 3: Documentation

**Files:**
- Create: `docs/local-demo-data.md`
- Modify: `README.md`
- Modify: `docs/v1-qa-checklist.md`

- [ ] **Step 1: Add local demo data guide**

Document migration, seed command, demo credentials, trial pages, and production warning.

- [ ] **Step 2: Link guide from README and V1 checklist**

Add references to `docs/local-demo-data.md`.

### Task 4: Verification And Handoff

**Files:**
- No new files unless verification reveals a small issue.

- [ ] **Step 1: Run Django check**

Run: `python manage.py check`

Expected: no issues.

- [ ] **Step 2: Run targeted tests**

Run: `python manage.py test core.tests_seed_demo_data`

Expected: tests pass.

- [ ] **Step 3: Run full app test suite**

Run: `python manage.py test accounts core documents invoices participants scheduling service_logs workers -v 1`

Expected: all app tests pass.

- [ ] **Step 4: Commit and push**

Commit:

```bash
git commit -m "feat: add local demo data seed command"
```
