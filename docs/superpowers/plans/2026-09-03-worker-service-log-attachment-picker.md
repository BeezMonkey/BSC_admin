# Worker Service Log Attachment Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make support worker service log attachment selection feel like an appendable, reviewable file list before submission.

**Architecture:** Keep the backend multipart POST unchanged and progressively enhance the existing file input with a small inline controller. CSS follows the existing worker form style and keeps native fallback usable when JavaScript is unavailable.

**Tech Stack:** Django templates, vanilla JavaScript, CSS, Django TestCase.

---

### Task 1: Attachment Picker Markup And Behavior

**Files:**
- Modify: `templates/service_logs/worker_service_log_form.html`
- Modify: `static/css/app.css`
- Test: `service_logs/tests_service_logs.py`

- [ ] Add a failing template test that expects worker attachment picker hooks, live file list text, remove action text, and max-file state text.
- [ ] Run the focused test and confirm it fails because the current form only renders the native file input.
- [ ] Replace the attachment section with progressive-enhancement markup around the existing `attachments` file input.
- [ ] Add vanilla JavaScript that appends selections, removes selected files, updates the input with `DataTransfer`, and disables adding at 3 files.
- [ ] Add CSS for the selected-file list, count text, add button, disabled state, and mobile layout.
- [ ] Run focused tests, then service log tests, then final project checks.
