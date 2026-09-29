# Service Log Invoice Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add participant and service-date filtering to the admin Service Logs workbench while retaining status-card, sorting, pagination, and invoice behaviour.

**Architecture:** A focused `service_logs.filters` module will resolve preset and custom service-date ranges. The existing list view will apply participant/date filters, calculate an unpaginated result summary, and build status-card URLs that preserve those filters. The existing template and stylesheet will render the approved compact layout without adding any model or invoice changes.

**Tech Stack:** Django 5, Django ORM, Django templates, existing CSS design system, Django `TestCase`/`SimpleTestCase`.

---

## File Structure

- Create `service_logs/filters.py`: date-range choices, Brisbane-relative preset calculation, custom-date parsing, and compact decimal-hour formatting.
- Create `service_logs/tests_filters.py`: pure unit coverage for all date presets, invalid values, custom bounds, and hour formatting.
- Modify `service_logs/views.py`: participant/date filtering, status-card query preservation, summary aggregation, and template context.
- Modify `service_logs/tests_review.py`: end-to-end list-view filtering, URL preservation, summaries, empty states, and invoice eligibility regression coverage.
- Modify `templates/service_logs/service_log_list.html`: compact filter row, hidden status state, participant/date controls, summary, and removal of the duplicate status dropdown.
- Modify `static/css/app.css`: desktop grid and responsive filter layout.
- Modify `core/tests_theme.py`: static assertions for the new layout hooks.

### Task 1: Date Range Resolver

**Files:**
- Create: `service_logs/filters.py`
- Create: `service_logs/tests_filters.py`

- [ ] **Step 1: Write failing resolver tests**

Create `service_logs/tests_filters.py` with a `SimpleTestCase` that fixes `today=date(2026, 9, 29)` and asserts:

```python
from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from service_logs.filters import format_hours, resolve_service_date_filter


class ServiceDateFilterTests(SimpleTestCase):
    def test_resolves_current_week_from_monday_to_sunday(self):
        result = resolve_service_date_filter("this_week", "", "", today=date(2026, 9, 29))
        self.assertEqual(result["start"], date(2026, 9, 28))
        self.assertEqual(result["end"], date(2026, 10, 4))

    def test_resolves_previous_and_current_billing_periods(self):
        expected = {
            "last_week": (date(2026, 9, 21), date(2026, 9, 27)),
            "this_fortnight": (date(2026, 9, 28), date(2026, 10, 11)),
            "last_fortnight": (date(2026, 9, 14), date(2026, 9, 27)),
            "this_month": (date(2026, 9, 1), date(2026, 9, 30)),
            "last_month": (date(2026, 8, 1), date(2026, 8, 31)),
        }
        for key, bounds in expected.items():
            with self.subTest(key=key):
                result = resolve_service_date_filter(key, "", "", today=date(2026, 9, 29))
                self.assertEqual((result["start"], result["end"]), bounds)

    def test_custom_range_accepts_open_and_reversed_bounds(self):
        result = resolve_service_date_filter("custom", "2026-09-20", "", today=date(2026, 9, 29))
        self.assertEqual(result["start"], date(2026, 9, 20))
        self.assertIsNone(result["end"])
        reversed_result = resolve_service_date_filter(
            "custom", "2026-09-30", "2026-09-01", today=date(2026, 9, 29)
        )
        self.assertGreater(reversed_result["start"], reversed_result["end"])

    def test_invalid_values_are_safe_and_preserved_for_correction(self):
        result = resolve_service_date_filter("unknown", "bad", "2026-99-99", today=date(2026, 9, 29))
        self.assertEqual(result["key"], "all")
        self.assertIsNone(result["start"])
        self.assertIsNone(result["end"])
        custom = resolve_service_date_filter("custom", "bad", "2026-99-99", today=date(2026, 9, 29))
        self.assertEqual(custom["start_value"], "bad")
        self.assertEqual(custom["end_value"], "2026-99-99")

    def test_formats_hours_without_unnecessary_zeroes(self):
        self.assertEqual(format_hours(Decimal("22.50")), "22.5")
        self.assertEqual(format_hours(None), "0")
```

- [ ] **Step 2: Run the resolver tests and verify RED**

Run:

```powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py test service_logs.tests_filters
```

Expected: import failure because `service_logs.filters` does not exist.

- [ ] **Step 3: Implement the minimal resolver**

Create `service_logs/filters.py` with:

```python
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from django.utils.dateparse import parse_date


DATE_RANGE_CHOICES = (
    ("all", "All dates"),
    ("this_week", "This week"),
    ("last_week", "Last week"),
    ("this_fortnight", "This fortnight"),
    ("last_fortnight", "Last fortnight"),
    ("this_month", "This month"),
    ("last_month", "Last month"),
    ("custom", "Custom"),
)


def _safe_parse_date(value):
    try:
        return parse_date(value) if value else None
    except ValueError:
        return None


def resolve_service_date_filter(key, start_value, end_value, *, today):
    valid_keys = {value for value, _label in DATE_RANGE_CHOICES}
    key = key if key in valid_keys else "all"
    monday = today - timedelta(days=today.weekday())
    ranges = {
        "this_week": (monday, monday + timedelta(days=6)),
        "last_week": (monday - timedelta(days=7), monday - timedelta(days=1)),
        "this_fortnight": (monday, monday + timedelta(days=13)),
        "last_fortnight": (monday - timedelta(days=14), monday - timedelta(days=1)),
        "this_month": (
            today.replace(day=1),
            today.replace(day=monthrange(today.year, today.month)[1]),
        ),
    }
    previous_month_last = today.replace(day=1) - timedelta(days=1)
    ranges["last_month"] = (previous_month_last.replace(day=1), previous_month_last)
    if key == "custom":
        start = _safe_parse_date(start_value)
        end = _safe_parse_date(end_value)
        return {"key": key, "start": start, "end": end, "start_value": start_value, "end_value": end_value}
    start, end = ranges.get(key, (None, None))
    return {
        "key": key,
        "start": start,
        "end": end,
        "start_value": start.isoformat() if start else "",
        "end_value": end.isoformat() if end else "",
    }


def format_hours(value):
    value = value or Decimal("0")
    return format(value.normalize(), "f")
```

- [ ] **Step 4: Run the resolver tests and verify GREEN**

Run the Task 1 test command again.

Expected: all resolver tests pass.

- [ ] **Step 5: Commit the resolver**

```powershell
git add service_logs/filters.py service_logs/tests_filters.py
git commit -m "feat: resolve service log date ranges"
```

### Task 2: Query Filtering and Preserved Navigation

**Files:**
- Modify: `service_logs/views.py:1-125`
- Modify: `service_logs/tests_review.py:448-654`

- [ ] **Step 1: Write failing list-view tests**

Add focused tests that create a second participant and logs inside/outside the requested dates. Assert:

```python
def test_service_log_list_filters_by_participant_and_service_date(self):
    other = Participant.objects.create(first_name="Julie", last_name="Steinback")
    inside_shift = Shift.objects.create(
        participant=other,
        worker=self.worker,
        service_date=date(2026, 9, 15),
        start_time=time(9, 0),
        end_time=time(12, 0),
        break_minutes=0,
        planned_hours=Decimal("3.00"),
        support_item=self.support_item,
        service_type=Shift.ServiceType.PERSONAL_CARE,
        status=Shift.Status.COMPLETED,
        created_by=self.admin_user,
    )
    inside_log = ServiceLog.objects.create_from_shift(
        shift=inside_shift,
        actual_start_time=time(9, 0),
        actual_end_time=time(12, 0),
        break_minutes=0,
        actual_hours=Decimal("3.00"),
        kilometres=Decimal("0"),
        case_notes="Inside requested period.",
        worker_notes="",
    )
    inside_log.status = ServiceLog.Status.APPROVED
    inside_log.save(update_fields=["status", "updated_at"])
    self.service_log.status = ServiceLog.Status.APPROVED
    self.service_log.save(update_fields=["status", "updated_at"])
    self.login_admin()
    response = self.client.get(
        reverse("service_log_list"),
        {
            "status": ServiceLog.Status.APPROVED,
            "participant": other.id,
            "date_range": "custom",
            "date_from": "2026-09-01",
            "date_to": "2026-09-30",
        },
    )
    self.assertEqual(response.context["pagination"]["record_count"], 1)
    self.assertEqual(response.context["selected_participant_id"], str(other.id))
    self.assertContains(response, "Julie Steinback")
    self.assertNotContains(response, "Ava Nguyen")

def test_status_cards_preserve_participant_and_service_dates(self):
    response = self.client.get(
        reverse("service_log_list"),
        {"participant": self.participant.id, "date_range": "this_month"},
    )
    self.assertContains(response, f"participant={self.participant.id}")
    self.assertContains(response, "date_range=this_month")

def test_clear_url_retains_status_only(self):
    response = self.client.get(
        reverse("service_log_list"),
        {"status": "approved", "participant": self.participant.id, "date_range": "this_month"},
    )
    self.assertEqual(response.context["clear_filter_url"], f'{reverse("service_log_list")}?status=approved')

def test_filtered_summary_uses_all_matches_before_pagination(self):
    response = self.client.get(reverse("service_log_list"), {"participant": self.participant.id})
    self.assertEqual(response.context["filtered_record_count"], 1)
    self.assertEqual(response.context["filtered_hours"], "2")
```

Also extend the existing pagination and sorting tests so expected URLs contain `participant`, `date_range`, `date_from`, and `date_to`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py test service_logs.tests_review.ServiceLogReviewTests
```

Expected: new assertions fail because the view does not yet filter or expose the new context.

- [ ] **Step 3: Implement filtering in the list view**

Update `service_logs/views.py` to:

```python
from urllib.parse import urlencode

from django.db.models import Count, Sum

from participants.models import Participant
from service_logs.filters import DATE_RANGE_CHOICES, format_hours, resolve_service_date_filter
```

In `service_log_list`:

```python
participants = Participant.objects.all()
participant_value = request.GET.get("participant", "").strip()
date_filter = resolve_service_date_filter(
    request.GET.get("date_range", "all").strip(),
    request.GET.get("date_from", "").strip(),
    request.GET.get("date_to", "").strip(),
    today=timezone.localdate(),
)
selected_participant = None
if participant_value:
    try:
        selected_participant = participants.filter(pk=int(participant_value)).first()
    except (TypeError, ValueError):
        selected_participant = None
    service_logs = (
        service_logs.filter(participant=selected_participant)
        if selected_participant
        else service_logs.none()
    )
if date_filter["start"]:
    service_logs = service_logs.filter(service_date__gte=date_filter["start"])
if date_filter["end"]:
    service_logs = service_logs.filter(service_date__lte=date_filter["end"])
summary = service_logs.aggregate(record_count=Count("id"), total_hours=Sum("actual_hours"))
```

Build status-card URLs from only `participant`, `date_range`, `date_from`, and `date_to`, adding the target status and dropping `page`. Build `clear_filter_url` from the active status only. Pass participant choices, selected values, date choices, effective dates, count, and formatted hours to the template. Remove `status_choices` from context.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 2 test command again.

Expected: all list-view tests pass.

- [ ] **Step 5: Commit queryset behaviour**

```powershell
git add service_logs/views.py service_logs/tests_review.py
git commit -m "feat: filter service logs for invoicing"
```

### Task 3: Compact Filter Interface

**Files:**
- Modify: `templates/service_logs/service_log_list.html:29-49`
- Modify: `static/css/app.css:1859-1864,6073-6085,6368-6376`
- Modify: `core/tests_theme.py`
- Modify: `service_logs/tests_review.py`

- [ ] **Step 1: Write failing template and theme tests**

Add assertions that the rendered page:

```python
self.assertContains(response, 'name="participant"')
self.assertContains(response, 'name="date_range"')
self.assertContains(response, 'name="date_from"')
self.assertContains(response, 'name="date_to"')
self.assertContains(response, 'name="status" value="approved"')
self.assertNotContains(response, '<select name="status">')
self.assertContains(response, 'class="service-log-filter-actions"')
self.assertContains(response, 'class="service-log-filter-summary"')
```

Add static CSS assertions for `.service-log-filter-bar`, `.service-log-filter-actions`, `.service-log-filter-summary`, and the responsive grid rule.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py test service_logs.tests_review core.tests_theme
```

Expected: the new markup/style assertions fail.

- [ ] **Step 3: Replace the duplicate status dropdown with the approved controls**

Use the following template structure:

```django
<form method="get" class="filter-bar service-log-filter-bar">
  {% if status %}<input type="hidden" name="status" value="{{ status }}">{% endif %}
  <label>Participant
    <select name="participant">
      <option value="">All participants</option>
      {% for participant in participants %}
        <option value="{{ participant.id }}"{% if selected_participant_id == participant.id|stringformat:"s" %} selected{% endif %}>{{ participant.display_name }}</option>
      {% endfor %}
    </select>
  </label>
  <label>Date range
    <select name="date_range">
      {% for value, label in date_range_choices %}
        <option value="{{ value }}"{% if date_range == value %} selected{% endif %}>{{ label }}</option>
      {% endfor %}
    </select>
  </label>
  <label>Service date from<input type="date" name="date_from" value="{{ date_from }}"></label>
  <label>Service date to<input type="date" name="date_to" value="{{ date_to }}"></label>
  <div class="service-log-filter-actions">
    <button type="submit">Filter</button>
    <a class="button secondary" href="{{ clear_filter_url }}">Clear</a>
  </div>
</form>
<div class="service-log-filter-summary">
  Showing <strong>{{ filtered_record_count }}{% if status_label %} {{ status_label|lower }}{% endif %} log{{ filtered_record_count|pluralize }}</strong>
  <span aria-hidden="true">·</span>
  {{ filtered_hours }} hours
</div>
```

Retain the existing full-reset link in the table's filtered-empty state.

- [ ] **Step 4: Add compact and responsive CSS**

Implement a five-column desktop grid for Participant, Date range, From, To, and actions. At tablet width, switch to two columns with full-width actions; at mobile width, switch to one column. Keep existing control heights and button styling.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 3 test command again.

Expected: Service Logs and theme tests pass.

- [ ] **Step 6: Commit the interface**

```powershell
git add templates/service_logs/service_log_list.html static/css/app.css core/tests_theme.py service_logs/tests_review.py
git commit -m "style: add compact service log invoice filters"
```

### Task 4: Regression Verification and Pull Request Readiness

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run Service Logs, invoices, and theme tests**

```powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py test service_logs invoices core.tests_theme
```

Expected: all tests pass.

- [ ] **Step 2: Run Django deployment checks**

```powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py check
git diff --check
```

Expected: no Django errors and no whitespace errors.

- [ ] **Step 3: Inspect the final branch diff**

```powershell
git status --short
git diff origin/staging...HEAD --stat
git diff origin/staging...HEAD -- service_logs/filters.py service_logs/views.py templates/service_logs/service_log_list.html static/css/app.css
```

Confirm there are no model, migration, invoice-calculation, or PDF changes.

- [ ] **Step 4: Push and create a PR targeting `staging`**

```powershell
git push -u origin codex/service-log-invoice-filters
gh pr create --base staging --head codex/service-log-invoice-filters --title "Filter service logs for invoicing" --body "Adds single-participant and service-date filters to the admin Service Logs workbench. Preserves status cards, sorting, pagination, approval, and invoice validation."
```

Attach the created PR to this task and report the staging verification steps to the user.
