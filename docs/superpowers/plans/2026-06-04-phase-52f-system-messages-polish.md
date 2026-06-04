# Phase 52F System Messages Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render and polish existing Django system messages without changing business behavior.

**Architecture:** Use Django's existing `messages` context processor in the admin and worker base templates. Add shared CSS selectors for message containers and semantic message levels.

**Tech Stack:** Django templates, CSS, Django TestCase.

---

### Task 1: Message Rendering Regression Test

**Files:**
- Modify: `participants/tests.py`

- [x] Add a failing test that creates a participant with `follow=True` and asserts `Participant created.` renders inside a success message.
- [x] Run the focused test and confirm it fails before implementation.

### Task 2: Render Messages in Shells

**Files:**
- Modify: `templates/admin_base.html`
- Modify: `templates/worker_base.html`

- [x] Add a shared message block below the topbar and above page content.
- [x] Preserve all existing navigation, logout, content blocks, redirects, and message text.

### Task 3: Message CSS

**Files:**
- Modify: `static/css/app.css`

- [x] Style `.messages` and `.message`.
- [x] Add semantic variants for `.success`, `.error`, `.warning`, and `.info`.
- [x] Keep message boxes compact and readable on desktop and mobile.

### Task 4: Verification

- [x] Run `python manage.py check`.
- [x] Run the focused message rendering test.
- [x] Run representative admin and worker app tests.
- [x] Run full `python manage.py test`.
- [ ] Commit and push the branch.
