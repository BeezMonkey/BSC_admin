# Quick Roster Planner Three Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Quick Roster Planner into three distinct Daily, Participant, and Worker planning views with overlap-only conflict warnings and worker hours for the selected date range.

**Architecture:** Keep the existing Shift model and all shift actions unchanged. Build view-specific presentation data in `roster_planner`, render shared shift tiles through a partial, and use CSS resource grids for Participant and Worker views while retaining the existing date-column layout for Daily overview.

**Tech Stack:** Django views/templates, Django TestCase, existing `static/css/app.css`, existing shift modal JavaScript.

---

### Task 1: Specify the three view modes

**Files:**
- Modify: `scheduling/tests_shifts.py`

- [ ] Add a failing test that expects the default `view_mode` to be `daily` and the page to render `Daily overview`.
- [ ] Add a failing test that requests `view=participant` and expects participant resource rows.
- [ ] Add a failing test that requests `view=worker` and expects worker resource rows plus selected-range hours.
- [ ] Run the three tests and verify they fail because the new modes and resource context do not exist yet.

### Task 2: Specify overlap conflict warnings

**Files:**
- Modify: `scheduling/tests_shifts.py`

- [ ] Add two overlapping active shifts for the same worker and date and assert one conflict plus both marked shifts.
- [ ] Add an overlapping cancelled shift and assert that it does not add a conflict.
- [ ] Run the conflict tests and verify they fail because planner conflict context does not exist yet.

### Task 3: Build planner presentation data

**Files:**
- Modify: `scheduling/views.py`

- [ ] Accept `daily`, `participant`, and `worker`, defaulting invalid or missing values to `daily`.
- [ ] Compute active overlap pairs from all shifts in the selected date range and mark displayed shifts without changing database records.
- [ ] Build participant or worker resource rows containing one cell per selected date.
- [ ] Sum `planned_hours` per worker and format the label as `this week` for seven days or `selected range` otherwise.
- [ ] Build mode-switch URLs that preserve dates and filters.
- [ ] Run the planner tests and verify the context-level assertions pass.

### Task 4: Render and style the three views

**Files:**
- Create: `templates/scheduling/_planner_shift_tile.html`
- Modify: `templates/scheduling/roster_planner.html`
- Modify: `static/css/app.css`

- [ ] Replace the View dropdown with a three-option segmented navigation.
- [ ] Keep Daily overview as the existing date-column calendar.
- [ ] Render Participant and Worker modes as resource rows across the selected dates.
- [ ] Render the worker hours label only in Worker view.
- [ ] Show the overlap summary banner and conflict labels only when active overlaps exist.
- [ ] Preserve every current shift action and modal URL in the shared tile partial.
- [ ] Keep the grid horizontally scrollable on smaller screens and the filters stacked at existing breakpoints.
- [ ] Run `scheduling.tests_shifts`, `manage.py check`, `git diff --check`, and inspect the final diff.
