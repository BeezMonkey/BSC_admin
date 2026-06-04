# Phase 52C Table and List Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish admin table/list views without changing behavior.

**Architecture:** Keep existing table templates and class names. Refine the existing CSS rules for `.table-card`, `table`, `th`, `td`, `.actions`, `.pagination`, and `.empty-state`.

**Tech Stack:** CSS and Django TestCase.

---

### Task 1: Pagination Regression Test

**Files:**
- Modify: `participants/tests.py`

- [ ] Add a lightweight assertion that paginated participant lists render the pagination nav class.
- [ ] Run the focused participant pagination test.

### Task 2: Table/List CSS Polish

**Files:**
- Modify: `static/css/app.css`

- [ ] Refine table container padding, header styling, row hover, action link buttons, pagination controls, and empty state spacing.
- [ ] Preserve all existing selectors and behavior.

### Task 3: Verification

- [ ] Run `python manage.py check`.
- [ ] Run representative list app tests.
- [ ] Run full `python manage.py test`.
- [ ] Commit and push the branch.
