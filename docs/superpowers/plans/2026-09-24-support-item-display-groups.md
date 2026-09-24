# Support Item Display Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `Core Supports` in the searchable picker with useful service-family headings without changing support item values or invoice behavior.

**Architecture:** Add one presentation-only grouping helper beside the picker widget and write the derived heading to the existing `data-category` attribute. Keep the native select, queryset, labels, values, and database schema unchanged; adjust only picker typography in the shared stylesheet.

**Tech Stack:** Django forms/widgets, Django TestCase, vanilla JavaScript, CSS.

---

### Task 1: Lock the display grouping contract

**Files:**
- Modify: `scheduling/tests_support_item_picker.py`
- Modify: `service_logs/tests_support_item_picker.py`

- [x] Add failing assertions for Self-care, Community access, Provider travel, Support coordination, and category fallback headings.
- [x] Assert rendered option values and full labels remain unchanged.
- [x] Run the focused picker tests and confirm the new assertions fail because `Core Supports` is still rendered.

### Task 2: Add presentation-only groups

**Files:**
- Modify: `scheduling/widgets.py`

- [x] Add a small case-insensitive helper that maps known item-name families to the approved display headings.
- [x] Use the helper only for the option `data-category` attribute.
- [x] Run the focused picker tests and confirm they pass.

### Task 3: Refine picker typography

**Files:**
- Modify: `static/css/app.css`
- Test: `scheduling/tests_support_item_picker.py`

- [x] Add a source-level regression assertion for the approved compact option and heading font sizes.
- [x] Run the test and confirm it fails before the stylesheet changes.
- [x] Reduce only the picker heading and option font sizes; retain existing row heights and mobile spacing.
- [x] Run focused and full test suites. The focused suite passes; the full suite has two pre-existing failures outside this change.

### Task 4: Deliver through the existing pull request

**Files:**
- Modify: the files listed above

- [x] Review the diff for schema, label, value, and invoice changes.
- [ ] Commit and push `codex/support-item-picker-style`.
- [ ] Confirm the existing pull request reflects the new commit.
