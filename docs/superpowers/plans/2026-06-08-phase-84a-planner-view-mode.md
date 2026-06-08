# Phase 84A Planner View Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit Participant and Worker view modes to Quick Roster Planner without changing the existing 7-day grid or adding shift copy/delete actions.

**Architecture:** Keep `roster_planner` as the single planner view. Add a `view_mode` GET parameter, derive view labels/context in `scheduling/views.py`, and update `templates/scheduling/roster_planner.html` to show the selected mode and clearer primary/secondary filter labels. Tests cover URL state, labels, and worker-filter behavior.

**Tech Stack:** Django views/templates/tests, existing CSS in `static/css/app.css`.

---

### Task 1: Add View Mode Tests

**Files:**
- Modify: `scheduling/tests_shifts.py`

- [ ] **Step 1: Write failing tests**

Add tests to `ShiftSchedulingTests`:

```python
def test_roster_planner_defaults_to_participant_view(self):
    self.login_admin()

    response = self.client.get(reverse("roster_planner"))

    self.assertEqual(response.status_code, 200)
    self.assertContains(response, "Participant view")
    self.assertContains(response, "Participant focus")
    self.assertContains(response, "Worker filter")

def test_roster_planner_worker_view_labels_and_filters(self):
    self.login_admin()
    other_worker = SupportWorker.objects.create(
        first_name="Jerry",
        last_name="Worker",
        email="jerry@example.com",
        phone="0400000002",
        status=SupportWorker.Status.ACTIVE,
    )
    Shift.objects.create(
        participant=self.participant,
        worker=other_worker,
        support_item=self.support_item,
        service_date=date(2026, 6, 2),
        start_time=time(9, 0),
        end_time=time(10, 0),
        status=Shift.Status.DRAFT,
        created_by=self.admin_user,
    )

    response = self.client.get(
        reverse("roster_planner"),
        {
            "view": "worker",
            "worker": self.worker.id,
            "date_from": "2026-06-01",
            "date_to": "2026-06-07",
        },
    )

    self.assertEqual(response.status_code, 200)
    self.assertContains(response, "Worker view")
    self.assertContains(response, "Worker focus")
    self.assertContains(response, "Participant filter")
    self.assertContains(response, self.worker.display_name)
    self.assertNotContains(response, other_worker.display_name)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_defaults_to_participant_view scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_worker_view_labels_and_filters
```

Expected: tests fail because planner has no view-mode labels.

### Task 2: Implement View Mode Context

**Files:**
- Modify: `scheduling/views.py`
- Modify: `templates/scheduling/roster_planner.html`

- [ ] **Step 1: Add view mode context in `roster_planner`**

Add:

```python
view_mode = request.GET.get("view", "participant").strip()
if view_mode not in {"participant", "worker"}:
    view_mode = "participant"
is_worker_view = view_mode == "worker"
```

Include in render context:

```python
"view_mode": view_mode,
"is_worker_view": is_worker_view,
"primary_filter_label": "Worker focus" if is_worker_view else "Participant focus",
"secondary_filter_label": "Participant filter" if is_worker_view else "Worker filter",
```

Update day add links so `view` is preserved in `add_shift_params`.

- [ ] **Step 2: Update planner template controls**

Add a `View` select to the filter form:

```html
<label>
  View
  <select name="view">
    <option value="participant" {% if view_mode == "participant" %}selected{% endif %}>Participant view</option>
    <option value="worker" {% if view_mode == "worker" %}selected{% endif %}>Worker view</option>
  </select>
</label>
```

Render the participant/worker filters with mode-aware labels using `primary_filter_label` and `secondary_filter_label`.

### Task 3: Verify And Commit

**Files:**
- Modify: `scheduling/tests_shifts.py`
- Modify: `scheduling/views.py`
- Modify: `templates/scheduling/roster_planner.html`

- [ ] **Step 1: Run targeted tests**

```powershell
.\.venv\Scripts\python.exe manage.py test scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_defaults_to_participant_view scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_worker_view_labels_and_filters
```

- [ ] **Step 2: Run planner regression tests**

```powershell
.\.venv\Scripts\python.exe manage.py test scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_filters_existing_shifts scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_renders_date_grid_with_empty_days scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_marks_weekly_grid_and_weekends scheduling.tests_shifts.ShiftSchedulingTests.test_roster_planner_day_links_prefill_new_shift
```

- [ ] **Step 3: Run system check**

```powershell
.\.venv\Scripts\python.exe manage.py check
```

- [ ] **Step 4: Commit**

```powershell
git add scheduling/tests_shifts.py scheduling/views.py templates/scheduling/roster_planner.html docs/superpowers/plans/2026-06-08-phase-84a-planner-view-mode.md
git commit -m "feat: add planner view mode"
```
