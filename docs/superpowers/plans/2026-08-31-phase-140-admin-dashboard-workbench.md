# Phase 140 Admin Dashboard Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the admin dashboard into a compact daily workbench with key counts, a priority queue, the existing workflow checklist, and common module actions.

**Architecture:** Keep all work inside the existing Django dashboard surface. `core.views.admin_dashboard` prepares simple context data, `templates/core/admin_dashboard.html` renders declarative sections, and `static/css/app.css` handles the compact workbench layout without changing routes, permissions, models, or POST workflows.

**Tech Stack:** Django 5.2, Django templates, existing CSS in `static/css/app.css`, Django `TestCase`.

---

## File Structure

- Modify: `core/views.py`
  - Add overview counts for active participants, active support workers, submitted service logs, and approved logs ready for invoice.
  - Convert the existing operations summary into a structured `priority_queue` list.
  - Keep the current `workflow_checklist` behavior and links.
  - Add a `module_links` list so the template does not hardcode repeated card markup.
- Modify: `templates/core/admin_dashboard.html`
  - Rename the page heading toward `Today at BSC`.
  - Render the compact overview strip.
  - Render the priority queue as the primary work area.
  - Keep workflow checklist as the secondary guide.
  - Render common module actions as compact shortcuts below the main work areas.
  - Do not add recent activity in the first implementation; keep the page light.
- Modify: `static/css/app.css`
  - Add compact workbench selectors for overview metrics, priority queue rows, and module actions.
  - Reuse current BSC tokens and card rhythm.
  - Keep responsive behavior clean at tablet and narrow mobile widths.
- Modify: `core/tests_dashboards.py`
  - Add focused tests for overview counts, priority queue ordering/links, zero-state behavior, and module links.
  - Preserve existing dashboard access, sidebar, workflow checklist, and worker dashboard tests.

## Task 1: Add Failing Dashboard Workbench Tests

**Files:**
- Modify: `core/tests_dashboards.py`
- Test: `core/tests_dashboards.py`

- [ ] **Step 1: Add a failing test for overview metrics, priority queue ordering, and links**

Add this test method inside `DashboardPolishTests`, after `test_admin_dashboard_shows_operations_summary`:

```python
    def test_admin_dashboard_shows_compact_workbench_overview_and_priority_queue(self):
        admin_user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
        worker_user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        worker = SupportWorker.objects.create(
            user=worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        inactive_worker_user = User.objects.create_user(username="inactiveworker", password="pass")
        UserProfile.objects.create(
            user=inactive_worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=inactive_worker_user,
            first_name="Inactive",
            last_name="Worker",
            email="inactive.worker@example.com",
            status=SupportWorker.Status.INACTIVE,
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        Participant.objects.create(
            first_name="Inactive",
            last_name="Participant",
            status=Participant.Status.INACTIVE,
            address_line_1="20 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        base_shift = {
            "participant": participant,
            "worker": worker,
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "planned_hours": Decimal("2.00"),
            "support_item": support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "created_by": admin_user,
        }
        Shift.objects.create(
            **base_shift,
            service_date=date(2026, 8, 31),
            status=Shift.Status.DRAFT,
        )
        submitted_shift = Shift.objects.create(
            **base_shift,
            service_date=date(2026, 9, 1),
            status=Shift.Status.COMPLETED,
        )
        approved_shift = Shift.objects.create(
            **base_shift,
            service_date=date(2026, 9, 2),
            status=Shift.Status.COMPLETED,
        )
        ServiceLog.objects.create_from_shift(
            shift=submitted_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            actual_hours=Decimal("2.00"),
            case_notes="Submitted log for review.",
            status=ServiceLog.Status.SUBMITTED,
        )
        ServiceLog.objects.create_from_shift(
            shift=approved_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            actual_hours=Decimal("2.00"),
            case_notes="Approved log awaiting invoice.",
            status=ServiceLog.Status.APPROVED,
        )
        Invoice.objects.create(
            participant=participant,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            status=Invoice.Status.DRAFT,
            created_by=admin_user,
        )
        Invoice.objects.create(
            participant=participant,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            status=Invoice.Status.ISSUED,
            created_by=admin_user,
        )

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))
        content = response.content.decode()

        self.assertContains(response, "Today at BSC")
        self.assertContains(response, "Operations overview")
        self.assertContains(response, "1 active participant")
        self.assertContains(response, "1 active support worker")
        self.assertContains(response, "1 submitted log")
        self.assertContains(response, "1 ready to invoice")
        self.assertContains(response, "Priority queue")
        self.assertContains(response, "Review submitted service logs")
        self.assertContains(response, "Create invoices from approved logs")
        self.assertContains(response, "Publish draft roster shifts")
        self.assertContains(response, "Check draft invoices")
        self.assertContains(response, "Follow up issued invoices")
        self.assertContains(response, f'{reverse("service_log_list")}?status={ServiceLog.Status.SUBMITTED}')
        self.assertContains(response, f'{reverse("service_log_list")}?status={ServiceLog.Status.APPROVED}')
        self.assertContains(response, f'{reverse("roster_list")}?status={Shift.Status.DRAFT}')
        self.assertContains(response, f'{reverse("invoice_placeholder")}?status={Invoice.Status.DRAFT}')
        self.assertContains(response, f'{reverse("invoice_placeholder")}?status={Invoice.Status.ISSUED}')
        self.assertLess(content.index("Review submitted service logs"), content.index("Create invoices from approved logs"))
        self.assertLess(content.index("Create invoices from approved logs"), content.index("Publish draft roster shifts"))
        self.assertLess(content.index("Publish draft roster shifts"), content.index("Check draft invoices"))
        self.assertLess(content.index("Check draft invoices"), content.index("Follow up issued invoices"))
```

- [ ] **Step 2: Add a failing test for compact module actions**

Add this test method after `test_admin_dashboard_lists_current_v1_modules`:

```python
    def test_admin_dashboard_shows_common_module_actions(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, "Common actions")
        self.assertContains(response, "Add participant")
        self.assertContains(response, "Add worker")
        self.assertContains(response, "Create shift")
        self.assertContains(response, "Review logs")
        self.assertContains(response, "Create invoice")
        self.assertContains(response, "Upload document")
        self.assertContains(response, reverse("participant_create"))
        self.assertContains(response, reverse("worker_create"))
        self.assertContains(response, reverse("shift_create"))
        self.assertContains(response, reverse("service_log_list"))
        self.assertContains(response, reverse("invoice_create"))
        self.assertContains(response, reverse("document_create"))
```

- [ ] **Step 3: Run the new tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_compact_workbench_overview_and_priority_queue core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_common_module_actions
```

Expected: FAIL because `Today at BSC`, `Operations overview`, `Priority queue`, and `Common actions` are not implemented yet.

## Task 2: Implement Dashboard Context Data

**Files:**
- Modify: `core/views.py`
- Test: `core/tests_dashboards.py`

- [ ] **Step 1: Import `SupportWorker`**

Update the imports at the top of `core/views.py`:

```python
from workers.models import SupportWorker
```

- [ ] **Step 2: Add overview counts and priority queue rows**

Inside `admin_dashboard`, after the existing count variables are calculated, add active counts and structured context:

```python
    active_participant_count = Participant.objects.filter(status=Participant.Status.ACTIVE).count()
    active_worker_count = SupportWorker.objects.filter(status=SupportWorker.Status.ACTIVE).count()
    operations_overview = [
        {
            "label": count_label(active_participant_count, "active participant"),
            "description": "Current participant records",
            "url_name": "participant_list",
            "query": f"status={Participant.Status.ACTIVE}",
        },
        {
            "label": count_label(active_worker_count, "active support worker"),
            "description": "Workers available for operations",
            "url_name": "worker_list",
            "query": f"status={SupportWorker.Status.ACTIVE}",
        },
        {
            "label": count_label(submitted_log_count, "submitted log"),
            "description": "Waiting for review",
            "url_name": "service_log_list",
            "query": f"status={ServiceLog.Status.SUBMITTED}",
        },
        {
            "label": count_label(approved_log_count, "ready to invoice", "ready to invoice"),
            "description": "Approved logs not billed",
            "url_name": "service_log_list",
            "query": f"status={ServiceLog.Status.APPROVED}",
        },
    ]
    priority_queue = [
        {
            "count": submitted_log_count,
            "label": count_label(submitted_log_count, "submitted log"),
            "action": "Review submitted service logs",
            "description": "Worker notes waiting for admin approval.",
            "url_name": "service_log_list",
            "query": f"status={ServiceLog.Status.SUBMITTED}",
            "kind": "review",
        },
        {
            "count": approved_log_count,
            "label": count_label(approved_log_count, "approved log"),
            "action": "Create invoices from approved logs",
            "description": "Approved support records not billed yet.",
            "url_name": "service_log_list",
            "query": f"status={ServiceLog.Status.APPROVED}",
            "kind": "invoice-ready",
        },
        {
            "count": draft_shift_count,
            "label": count_label(draft_shift_count, "draft shift"),
            "action": "Publish draft roster shifts",
            "description": "Workers cannot see draft shifts until they are published.",
            "url_name": "roster_list",
            "query": f"status={Shift.Status.DRAFT}",
            "kind": "roster",
        },
        {
            "count": draft_invoice_count,
            "label": count_label(draft_invoice_count, "draft invoice"),
            "action": "Check draft invoices",
            "description": "Review draft billing before issuing.",
            "url_name": "invoice_placeholder",
            "query": f"status={Invoice.Status.DRAFT}",
            "kind": "invoice-draft",
        },
        {
            "count": issued_invoice_count,
            "label": count_label(issued_invoice_count, "issued invoice"),
            "action": "Follow up issued invoices",
            "description": "Track invoices that have been issued but not marked paid.",
            "url_name": "invoice_placeholder",
            "query": f"status={Invoice.Status.ISSUED}",
            "kind": "invoice-issued",
        },
    ]
    active_priority_queue = [item for item in priority_queue if item["count"]]
```

- [ ] **Step 3: Add common module actions**

Still inside `admin_dashboard`, before `return render`, add:

```python
    module_links = [
        {
            "label": "Add participant",
            "description": "Create a client record",
            "url_name": "participant_create",
        },
        {
            "label": "Add worker",
            "description": "Create a support worker",
            "url_name": "worker_create",
        },
        {
            "label": "Create shift",
            "description": "Add roster support",
            "url_name": "shift_create",
        },
        {
            "label": "Review logs",
            "description": "Open service logs",
            "url_name": "service_log_list",
        },
        {
            "label": "Create invoice",
            "description": "Bill approved support",
            "url_name": "invoice_create",
        },
        {
            "label": "Upload document",
            "description": "Share a record",
            "url_name": "document_create",
        },
    ]
```

- [ ] **Step 4: Pass new context to the template**

Update the `render` context:

```python
        {
            "operations_overview": operations_overview,
            "priority_queue": active_priority_queue,
            "operations_summary": operations_summary,
            "workflow_checklist": workflow_checklist,
            "module_links": module_links,
        },
```

Keep `operations_summary` for compatibility with existing tests until the template is updated.

- [ ] **Step 5: Run the focused failing tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_compact_workbench_overview_and_priority_queue core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_common_module_actions
```

Expected: still FAIL because the template has not rendered the new context yet.

## Task 3: Render The Compact Workbench Template

**Files:**
- Modify: `templates/core/admin_dashboard.html`
- Test: `core/tests_dashboards.py`

- [ ] **Step 1: Replace the dashboard body with the workbench layout**

Replace `templates/core/admin_dashboard.html` with this structure:

```django
{% extends "admin_base.html" %}

{% block title %}Admin Dashboard - Brisbane Star Care{% endblock %}

{% block content %}
<header class="page-header dashboard-workbench-header">
  <div>
    <h1>Today at BSC</h1>
    <p>Review current admin follow-up work and continue the NDIS operations loop.</p>
  </div>
</header>

<section class="dashboard-overview-strip" aria-label="Operations overview">
  <div class="dashboard-section-heading">
    <h2>Operations overview</h2>
    <p>Key counts for the current admin workflow.</p>
  </div>
  <div class="operations-overview-grid">
    {% for item in operations_overview %}
    <a class="operations-overview-item" href="{% url item.url_name %}{% if item.query %}?{{ item.query }}{% endif %}">
      <strong>{{ item.label }}</strong>
      <span>{{ item.description }}</span>
    </a>
    {% endfor %}
  </div>
</section>

<div class="dashboard-overview dashboard-workbench-grid">
  <section class="card dashboard-card priority-queue">
    <div>
      <h2>Priority queue</h2>
      <p>Start here when you need to know what to handle first.</p>
    </div>
    {% if priority_queue %}
    <div class="priority-queue-list">
      {% for item in priority_queue %}
      <a class="priority-queue-item {{ item.kind }}" href="{% url item.url_name %}{% if item.query %}?{{ item.query }}{% endif %}">
        <span class="priority-queue-count">{{ item.count }}</span>
        <span class="priority-queue-copy">
          <strong>{{ item.action }}</strong>
          <span>{{ item.description }}</span>
        </span>
        <span class="priority-queue-label">{{ item.label }}</span>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="summary-empty-state">
      <strong>No outstanding admin actions.</strong>
      <span>New roster, service log, and invoice tasks are listed here.</span>
    </div>
    {% endif %}
  </section>

  <section class="card dashboard-card workflow-checklist">
    <div class="workflow-checklist-header">
      <div>
        <h2>Workflow checklist</h2>
        <p>Follow the usual path from participant setup through invoicing.</p>
      </div>
      <span class="workflow-checklist-badge">V1 guide</span>
    </div>
    <ol class="workflow-checklist-list">
      {% for item in workflow_checklist %}
      <li>
        <span class="workflow-checklist-number">{{ forloop.counter }}</span>
        <div class="workflow-checklist-copy">
          <strong>{{ item.label }}</strong>
          <span>{{ item.description }}</span>
        </div>
        <div class="workflow-checklist-action">
          <span>{{ item.detail }}</span>
          <a href="{% url item.url_name %}{% if item.query %}?{{ item.query }}{% endif %}">Open</a>
        </div>
      </li>
      {% endfor %}
    </ol>
  </section>
</div>

<section class="card dashboard-card common-actions">
  <div class="dashboard-section-heading">
    <h2>Common actions</h2>
    <p>Frequently used admin shortcuts.</p>
  </div>
  <div class="common-actions-grid">
    {% for item in module_links %}
    <a class="common-action-item" href="{% url item.url_name %}">
      <strong>{{ item.label }}</strong>
      <span>{{ item.description }}</span>
    </a>
    {% endfor %}
  </div>
</section>
{% endblock %}
```

- [ ] **Step 2: Run the focused dashboard tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_compact_workbench_overview_and_priority_queue core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_common_module_actions core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_zero_state_when_no_operations_need_action core.tests_dashboards.DashboardPolishTests.test_admin_dashboard_shows_workflow_checklist
```

Expected: PASS for content if view context is correct. Visual selector tests may still fail until CSS hooks are added.

## Task 4: Style The Compact Dashboard

**Files:**
- Modify: `static/css/app.css`
- Test: `core/tests_dashboards.py`, `core/tests_theme.py`

- [ ] **Step 1: Add compact workbench CSS**

Append this CSS near the existing dashboard styles around `.dashboard-overview`:

```css
.dashboard-workbench-header {
  margin-bottom: 1rem;
}

.dashboard-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.dashboard-section-heading h2 {
  margin: 0;
  font-size: 1rem;
}

.dashboard-section-heading p {
  margin: 0.18rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.45;
}

.dashboard-overview-strip {
  display: grid;
  gap: 0.8rem;
  margin-bottom: 1rem;
}

.operations-overview-grid,
.common-actions-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.72rem;
}

.operations-overview-item,
.common-action-item {
  display: grid;
  gap: 0.25rem;
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 0.82rem 0.9rem;
  background: #ffffff;
}

.operations-overview-item:hover,
.common-action-item:hover {
  border-color: var(--brand);
  background: #f8fffd;
}

.operations-overview-item strong,
.common-action-item strong {
  color: var(--ink);
  font-size: 0.95rem;
  line-height: 1.25;
}

.operations-overview-item span,
.common-action-item span {
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.35;
}

.dashboard-workbench-grid {
  grid-template-columns: minmax(26rem, 1.18fr) minmax(26rem, 0.82fr);
}

.priority-queue-list {
  display: grid;
  gap: 0.58rem;
}

.priority-queue-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 7px;
  padding: 0.72rem 0.82rem;
  background: #ffffff;
}

.priority-queue-item:hover {
  border-color: var(--brand);
  border-left-color: var(--brand);
  background: #f8fffd;
}

.priority-queue-item.invoice-ready,
.priority-queue-item.invoice-draft {
  border-left-color: var(--brand);
}

.priority-queue-item.invoice-issued {
  border-left-color: #64748b;
}

.priority-queue-count {
  display: inline-grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 7px;
  color: var(--brand-dark);
  background: #ccfbf1;
  font-weight: var(--weight-strong);
  line-height: 1;
}

.priority-queue-copy {
  display: grid;
  min-width: 0;
  gap: 0.16rem;
}

.priority-queue-copy strong {
  color: var(--ink);
  font-size: 0.95rem;
  line-height: 1.25;
}

.priority-queue-copy span {
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.35;
}

.priority-queue-label {
  color: var(--muted);
  font-size: 0.82rem;
  white-space: nowrap;
}

.common-actions {
  margin-top: 1rem;
}
```

- [ ] **Step 2: Add responsive CSS**

In the existing `@media (max-width: 1050px)` block, add:

```css
  .dashboard-workbench-grid,
  .operations-overview-grid,
  .common-actions-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
```

In the existing `@media (max-width: 760px)` block, add:

```css
  .operations-overview-grid,
  .common-actions-grid,
  .dashboard-workbench-grid {
    grid-template-columns: 1fr;
  }

  .priority-queue-item {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .priority-queue-label {
    grid-column: 2;
    white-space: normal;
  }
```

- [ ] **Step 3: Run dashboard and theme tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_dashboards core.tests_theme
```

Expected: PASS. If `core.tests_theme` expects old dashboard selectors, update those assertions only to include the new selector names; do not weaken unrelated theme checks.

## Task 5: Final Verification And Commit

**Files:**
- Modify: `core/views.py`
- Modify: `templates/core/admin_dashboard.html`
- Modify: `static/css/app.css`
- Modify: `core/tests_dashboards.py`
- Modify only if a current selector assertion fails: `core/tests_theme.py`

- [ ] **Step 1: Run focused regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_dashboards core.tests_theme accounts.tests
```

Expected: PASS.

- [ ] **Step 2: Run system check**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Expected: `System check identified no issues`.

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors. Windows line-ending warnings are acceptable if no whitespace errors are reported.

- [ ] **Step 4: Review final diff**

Run:

```powershell
git diff --stat
git diff -- core\views.py templates\core\admin_dashboard.html static\css\app.css core\tests_dashboards.py core\tests_theme.py
```

Expected: only dashboard workbench files changed. No permission, route, model, migration, or email settings changes.

- [ ] **Step 5: Commit implementation**

Run:

```powershell
git add core\views.py templates\core\admin_dashboard.html static\css\app.css core\tests_dashboards.py core\tests_theme.py
git commit -m "feat: refine admin dashboard workbench"
```

Expected: one implementation commit on `codex/phase-140-admin-dashboard-workbench`.

## Task 6: Optional Browser QA

**Files:**
- No source files unless QA reveals a defect.

- [ ] **Step 1: Start the local server**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Expected: local server starts without errors.

- [ ] **Step 2: Open the admin dashboard**

Open:

```text
http://127.0.0.1:8000/admin-dashboard/
```

Expected:

- The page heading reads `Today at BSC`.
- The overview strip is visible and compact.
- The priority queue appears before the workflow checklist.
- Common actions are below the main work areas.
- The page does not feel crowded on desktop.

- [ ] **Step 3: Check narrow width**

Use a 375px-wide browser viewport.

Expected:

- KPI tiles stack cleanly.
- Priority queue rows wrap without horizontal overflow.
- Workflow checklist remains readable.
- Common action cards stack in a single column.
