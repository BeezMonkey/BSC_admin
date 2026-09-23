# Portal Date and Time Style Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the approved Admin calendar and five-minute time picker presentation in SW service log forms and the SC coordination log form without changing business behaviour.

**Architecture:** Keep the existing Django forms, views, field names, and validation untouched. Render the existing fields through the shared `date_time_picker_field.html` partial, load the existing picker JavaScript only on the affected portal forms, and add portal-scoped layout CSS only if browser verification finds an integration issue.

**Tech Stack:** Django templates and tests, shared vanilla JavaScript picker, existing `static/css/app.css` and portal responsive layout.

---

### Task 1: Lock the SW template contract

**Files:**
- Modify: `service_logs/tests_service_logs.py`

- [x] **Step 1: Add failing scheduled and unscheduled form tests**

Add tests to `ServiceLogCompletionTests` that log in as the worker and assert:

```python
def test_scheduled_service_log_uses_shared_time_pickers(self):
    shift = self.create_shift(status=Shift.Status.CONFIRMED)
    self.login_worker()

    response = self.client.get(
        reverse("worker_service_log_create", args=[shift.id])
    )

    self.assertContains(response, 'data-date-time-picker="time"', count=2)
    self.assertNotContains(response, 'data-date-time-picker="date"')
    self.assertContains(response, '<input type="hidden" name="actual_start_time"')
    self.assertContains(response, '<input type="hidden" name="actual_end_time"')
    self.assertContains(response, "js/date_time_picker.")

def test_unscheduled_service_log_uses_shared_date_and_time_pickers(self):
    ParticipantWorkerAssignment.objects.create(
        participant=self.participant,
        worker=self.worker,
        start_date=date(2026, 1, 1),
        is_active=True,
    )
    self.login_worker()

    response = self.client.get(reverse("worker_unscheduled_service_log_create"))

    self.assertContains(response, 'data-date-time-picker="date"', count=1)
    self.assertContains(response, 'data-date-time-picker="time"', count=2)
    self.assertContains(response, '<input type="hidden" name="service_date"')
    self.assertContains(response, '<input type="hidden" name="actual_start_time"')
    self.assertContains(response, '<input type="hidden" name="actual_end_time"')
    self.assertContains(response, "js/date_time_picker.")
```

- [x] **Step 2: Run the SW tests and verify RED**

Run:

```powershell
python manage.py test service_logs.tests_service_logs.ServiceLogCompletionTests.test_scheduled_service_log_uses_shared_time_pickers service_logs.tests_service_logs.ServiceLogCompletionTests.test_unscheduled_service_log_uses_shared_date_and_time_pickers
```

Expected: both tests fail because the portal still renders native date/time inputs.

### Task 2: Render shared pickers in the SW form

**Files:**
- Modify: `templates/service_logs/worker_service_log_form.html`

- [x] **Step 1: Load the shared script and render the date field**

Load `static`, then replace only the unscheduled `service_date` label with:

```django
{% include "scheduling/partials/date_time_picker_field.html" with field=form.service_date picker_type="date" hint="Choose the service date." %}
```

Add the shared script once at the bottom of the template:

```django
<script src="{% static 'js/date_time_picker.js' %}" defer></script>
```

- [x] **Step 2: Render the actual-time fields**

Replace the native actual start and end time labels with:

```django
{% include "scheduling/partials/date_time_picker_field.html" with field=form.actual_start_time picker_type="time" hint="5-minute intervals" %}
{% include "scheduling/partials/date_time_picker_field.html" with field=form.actual_end_time picker_type="time" hint="5-minute intervals" %}
```

Leave participant, support item, service type, break minutes, kilometres, notes, attachments, buttons, and JavaScript attachment handling unchanged.

- [x] **Step 3: Run the SW tests and verify GREEN**

Run the two focused tests from Task 1. Expected: both pass.

### Task 3: Lock and implement the SC template contract

**Files:**
- Modify: `coordinators/tests.py`
- Modify: `templates/coordinators/sc_coordination_log_form.html`

- [x] **Step 1: Add the failing SC form test**

Add to `CoordinatorLogSubmissionTests`:

```python
def test_sc_log_form_uses_shared_date_and_time_pickers(self):
    response = self.client.get(reverse("coordinator_log_create"))

    self.assertContains(response, 'data-date-time-picker="date"', count=1)
    self.assertContains(response, 'data-date-time-picker="time"', count=2)
    self.assertContains(response, '<input type="hidden" name="service_date"')
    self.assertContains(response, '<input type="hidden" name="start_time"')
    self.assertContains(response, '<input type="hidden" name="end_time"')
    self.assertContains(response, "js/date_time_picker.")
```

- [x] **Step 2: Run the SC test and verify RED**

Run:

```powershell
python manage.py test coordinators.tests.CoordinatorLogSubmissionTests.test_sc_log_form_uses_shared_date_and_time_pickers
```

Expected: fail because the SC template still renders native date/time fields.

- [x] **Step 3: Render the shared fields and script**

Load `static`, replace only the three date/time includes with:

```django
{% include "scheduling/partials/date_time_picker_field.html" with field=form.service_date picker_type="date" hint="Choose the service date." %}
{% include "scheduling/partials/date_time_picker_field.html" with field=form.start_time picker_type="time" hint="5-minute intervals" %}
{% include "scheduling/partials/date_time_picker_field.html" with field=form.end_time picker_type="time" hint="5-minute intervals" %}
```

Load `js/date_time_picker.js` once at the bottom. Do not change any other SC fields or actions.

- [x] **Step 4: Run the SC test and verify GREEN**

Run the focused SC test. Expected: pass.

### Task 4: Verify unchanged behaviour and responsive layout

**Files:**
- Modify only if visual integration requires it: `static/css/portal.css`

- [x] **Step 1: Run behaviour regression suites**

Run:

```powershell
python manage.py test service_logs.tests_service_logs coordinators.tests
python manage.py check
```

Expected: all tests and system checks pass, including existing duration, break, participant assignment, submission, redirect, and status assertions.

- [x] **Step 2: Run static checks**

Run:

```powershell
$js = Get-Content -Raw static/js/date_time_picker.js
$js | node --check -
git diff --check
```

Expected: exit code 0 with no syntax or whitespace errors.

- [x] **Step 3: Perform browser verification**

At desktop and 390px mobile widths, inspect:

- scheduled SW Complete Service Log;
- SW Submit Unscheduled Service;
- SC Submit Coordination Log.

Verify the calendar, Sat/Sun emphasis, five-minute wheels, selected values, validation error display, viewport containment, and unchanged surrounding fields/actions. Add only portal-scoped layout CSS if required, then rerun the focused tests and static checks.

- [x] **Step 4: Commit and publish**

Commit the implementation, push `codex/portal-date-time-style`, create a PR against `main`, and attach the PR to the task.
