# Support Coordination Invoice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an Admin-only invoice workflow for approved Support Coordinator coordination logs without mixing them with existing Support Worker service-log invoices.

**Architecture:** Reuse the existing `Invoice` and `InvoiceLine` engine, but add an explicit `invoice_type` and mutually exclusive line sources: `service_log` for service invoices and `coordination_log` for support coordination invoices. Add a separate Admin create page and keep SC users out of all invoice workflows.

**Tech Stack:** Django models, migrations, forms, function-based views, Django templates, Django TestCase, existing PDF/CSV generator in `invoices/views.py`.

---

## File Map

- Modify: `invoices/models.py`
  - Add `Invoice.InvoiceType`.
  - Add `Invoice.invoice_type`.
  - Add nullable `InvoiceLine.coordination_log`.
  - Make `InvoiceLine.service_log` nullable.
  - Add `InvoiceLine.LineType.SUPPORT_COORDINATION`.
  - Add manager method `create_from_coordination_log`.
  - Add constraints to enforce exactly one source and prevent duplicate coordination billing.

- Create: `invoices/migrations/0004_support_coordination_invoice.py`
  - Add new fields and constraints.
  - Preserve existing invoice rows as `service`.

- Modify: `coordinators/models.py`
  - Add `CoordinationLog.Status.INVOICED`.

- Modify: `invoices/forms.py`
  - Add `SupportCoordinationInvoiceCreateForm`.

- Modify: `invoices/views.py`
  - Add billable coordination-log query helpers.
  - Add selected coordination-log grouping helpers.
  - Add `support_coordination_invoice_create`.
  - Make CSV/PDF source-date helpers support both service and coordination lines.
  - Make invoice filenames include `SC_Invoice` for support coordination invoices.
  - Release coordination logs on cancel/delete.

- Modify: `invoices/urls.py`
  - Add `/invoices/support-coordination/new/` route named `support_coordination_invoice_create`.

- Create: `templates/invoices/support_coordination_invoice_form.html`
  - Dedicated Admin create page for SC invoices.

- Create: `templates/invoices/support_coordination_invoice_rows.html`
  - Shared table markup for SC invoice preview rows.

- Modify: `templates/invoices/invoice_list.html`
  - Show invoice type label.

- Modify: `templates/invoices/invoice_detail.html`
  - Show invoice type in detail metadata.

- Modify: `templates/coordinators/coordination_log_list.html`
  - Add Admin billing action for approved coordination logs.

- Modify: `core/models.py`
  - Add `SUPPORT_COORDINATION_INVOICE_CREATED` audit action.

- Test: `invoices/tests_invoices.py`
  - Add model, create-flow, PDF/CSV, release, permissions, and regression tests.

- Test: `coordinators/tests.py`
  - Add Coordination Logs list checkbox/action test and invoiced status display behavior.

---

### Task 1: Add Model Contract Tests

**Files:**
- Modify: `invoices/tests_invoices.py`
- Modify: `coordinators/tests.py`

- [ ] **Step 1: Write failing tests for invoice source separation**

Add these tests near the existing invoice model tests in `invoices/tests_invoices.py`:

```python
from coordinators.models import CoordinationLog, SupportCoordinator


def create_coordinator_user(username="coord-invoice"):
    user = get_user_model().objects.create_user(
        username=username,
        password="test-password-123",
        email=f"{username}@example.com",
    )
    UserProfile.objects.create(user=user, role=UserProfile.Role.SUPPORT_COORDINATOR)
    return SupportCoordinator.objects.create(
        user=user,
        first_name="Casey",
        last_name="Coordinator",
        email=f"{username}@example.com",
    )
```

Inside `InvoiceGenerationTests`, add:

```python
def create_coordination_log(self, **overrides):
    coordinator = overrides.pop("coordinator", create_coordinator_user())
    participant = overrides.pop("participant", self.participant)
    status = overrides.pop("status", CoordinationLog.Status.APPROVED)
    service_date = overrides.pop("service_date", date(2026, 6, 1))
    actual_hours = overrides.pop("actual_hours", Decimal("1.50"))
    return CoordinationLog.objects.create(
        participant=participant,
        coordinator=coordinator,
        service_date=service_date,
        start_time=time(9, 0),
        end_time=time(10, 30),
        break_minutes=0,
        actual_hours=actual_hours,
        coordination_type=CoordinationLog.CoordinationType.GENERAL,
        case_notes="Coordination work for invoice.",
        status=status,
    )

def test_invoice_defaults_to_service_invoice_type(self):
    invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        created_by=self.accountant_user,
    )

    self.assertEqual(invoice.invoice_type, Invoice.InvoiceType.SERVICE)

def test_invoice_line_can_snapshot_support_coordination_log(self):
    coordination_log = self.create_coordination_log(actual_hours=Decimal("1.50"))
    invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 1),
        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        created_by=self.admin_user,
    )

    line = InvoiceLine.objects.create_from_coordination_log(
        invoice=invoice,
        coordination_log=coordination_log,
        support_item=self.support_item,
    )

    self.assertIsNone(line.service_log)
    self.assertEqual(line.coordination_log, coordination_log)
    self.assertEqual(line.line_type, InvoiceLine.LineType.SUPPORT_COORDINATION)
    self.assertEqual(line.quantity, Decimal("1.50"))
    self.assertEqual(line.unit_price, Decimal("65.47"))
    self.assertEqual(line.line_total, Decimal("98.21"))

def test_same_coordination_log_cannot_be_invoiced_twice(self):
    coordination_log = self.create_coordination_log()
    first_invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 1),
        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        created_by=self.admin_user,
    )
    second_invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 1),
        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        created_by=self.admin_user,
    )
    InvoiceLine.objects.create_from_coordination_log(
        invoice=first_invoice,
        coordination_log=coordination_log,
        support_item=self.support_item,
    )

    with self.assertRaises(IntegrityError):
        with transaction.atomic():
            InvoiceLine.objects.create_from_coordination_log(
                invoice=second_invoice,
                coordination_log=coordination_log,
                support_item=self.support_item,
            )
```

- [ ] **Step 2: Write failing test for coordination invoiced status**

Add to `CoordinatorModelTests` in `coordinators/tests.py`:

```python
def test_coordination_log_has_invoiced_status(self):
    choices = dict(CoordinationLog.Status.choices)

    self.assertEqual(choices[CoordinationLog.Status.INVOICED], "Invoiced")
```

- [ ] **Step 3: Run the focused tests and verify failure**

Run:

```bash
python manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_invoice_defaults_to_service_invoice_type invoices.tests_invoices.InvoiceGenerationTests.test_invoice_line_can_snapshot_support_coordination_log invoices.tests_invoices.InvoiceGenerationTests.test_same_coordination_log_cannot_be_invoiced_twice coordinators.tests.CoordinatorModelTests.test_coordination_log_has_invoiced_status
```

Expected:

- Failures mention missing `InvoiceType`, `invoice_type`, `coordination_log`, `create_from_coordination_log`, or `INVOICED`.

- [ ] **Step 4: Commit failing tests**

```bash
git add invoices/tests_invoices.py coordinators/tests.py
git commit -m "test: cover support coordination invoice model contracts"
```

---

### Task 2: Implement Model And Migration Changes

**Files:**
- Modify: `invoices/models.py`
- Modify: `coordinators/models.py`
- Create: `invoices/migrations/0004_support_coordination_invoice.py`

- [ ] **Step 1: Update `CoordinationLog.Status`**

In `coordinators/models.py`, change:

```python
class Status(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
```

to:

```python
class Status(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    INVOICED = "invoiced", "Invoiced"
```

- [ ] **Step 2: Update imports in `invoices/models.py`**

Add:

```python
from coordinators.models import CoordinationLog
```

- [ ] **Step 3: Add invoice type**

Inside `Invoice`, before `Status`, add:

```python
class InvoiceType(models.TextChoices):
    SERVICE = "service", "Service"
    SUPPORT_COORDINATION = "support_coordination", "Support Coordination"
```

Add this field after `invoice_number`:

```python
invoice_type = models.CharField(
    max_length=30,
    choices=InvoiceType.choices,
    default=InvoiceType.SERVICE,
)
```

- [ ] **Step 4: Add coordination invoice manager method**

Inside `InvoiceLineManager`, add:

```python
def create_from_coordination_log(self, invoice, coordination_log, support_item):
    quantity = coordination_log.actual_hours
    unit_price = support_item.price_limit
    line_total = (quantity * unit_price).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return self.create(
        invoice=invoice,
        coordination_log=coordination_log,
        line_type=InvoiceLine.LineType.SUPPORT_COORDINATION,
        support_item_number=support_item.item_number,
        description=support_item.name,
        unit=support_item.unit,
        unit_price=unit_price,
        quantity=quantity,
        gst_code=support_item.gst_code,
        line_total=line_total,
    )
```

- [ ] **Step 5: Update `InvoiceLine` source fields and line type**

Change `LineType` to:

```python
class LineType(models.TextChoices):
    SERVICE = "service", "Service"
    TRAVEL_NON_LABOUR = "travel_non_labour", "Provider travel - non-labour"
    SUPPORT_COORDINATION = "support_coordination", "Support Coordination"
```

Change `service_log` to:

```python
service_log = models.ForeignKey(
    ServiceLog,
    on_delete=models.PROTECT,
    related_name="invoice_lines",
    null=True,
    blank=True,
)
```

Add after `service_log`:

```python
coordination_log = models.ForeignKey(
    CoordinationLog,
    on_delete=models.PROTECT,
    related_name="invoice_lines",
    null=True,
    blank=True,
)
```

- [ ] **Step 6: Add constraints**

Replace the `constraints` list with:

```python
constraints = [
    models.UniqueConstraint(
        fields=["service_log", "line_type"],
        condition=models.Q(service_log__isnull=False),
        name="unique_invoice_line_type_per_service_log",
    ),
    models.UniqueConstraint(
        fields=["coordination_log"],
        condition=models.Q(coordination_log__isnull=False),
        name="unique_invoice_line_per_coordination_log",
    ),
    models.CheckConstraint(
        check=(
            models.Q(service_log__isnull=False, coordination_log__isnull=True)
            | models.Q(service_log__isnull=True, coordination_log__isnull=False)
        ),
        name="invoice_line_has_exactly_one_source",
    ),
]
```

- [ ] **Step 7: Create migration**

Run:

```bash
python manage.py makemigrations invoices
```

Expected:

- Creates `invoices/migrations/0004_support_coordination_invoice.py`.

- [ ] **Step 8: Run model tests**

Run:

```bash
python manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_invoice_defaults_to_service_invoice_type invoices.tests_invoices.InvoiceGenerationTests.test_invoice_line_can_snapshot_support_coordination_log invoices.tests_invoices.InvoiceGenerationTests.test_same_coordination_log_cannot_be_invoiced_twice coordinators.tests.CoordinatorModelTests.test_coordination_log_has_invoiced_status
```

Expected: all selected tests pass.

- [ ] **Step 9: Commit model changes**

```bash
git add invoices/models.py coordinators/models.py invoices/migrations/0004_support_coordination_invoice.py invoices/tests_invoices.py coordinators/tests.py
git commit -m "feat: add support coordination invoice data model"
```

---

### Task 3: Add SC Invoice Form And Query Helpers

**Files:**
- Modify: `invoices/forms.py`
- Modify: `invoices/views.py`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing tests for billable coordination log queries**

Add to `InvoiceGenerationTests`:

```python
def test_support_coordination_invoice_preview_shows_approved_uninvoiced_logs(self):
    approved_log = self.create_coordination_log(case_notes="Billable SC work.")
    self.create_coordination_log(status=CoordinationLog.Status.SUBMITTED, case_notes="Submitted SC work.")
    self.login_admin()

    response = self.client.get(
        reverse("support_coordination_invoice_create"),
        {
            "participant": self.participant.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "support_item": self.support_item.id,
        },
    )

    self.assertContains(response, "Billable SC work.")
    self.assertContains(response, f'name="coordination_log_ids" value="{approved_log.id}"')
    self.assertNotContains(response, "Submitted SC work.")

def test_support_coordination_invoice_create_requires_admin(self):
    self.login_accountant()

    response = self.client.get(reverse("support_coordination_invoice_create"))

    self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_preview_shows_approved_uninvoiced_logs invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_create_requires_admin
```

Expected:

- Failures mention missing route `support_coordination_invoice_create`.

- [ ] **Step 3: Add `SupportCoordinationInvoiceCreateForm`**

In `invoices/forms.py`, import `SupportItem`:

```python
from scheduling.models import SupportItem
```

Add:

```python
class SupportCoordinationInvoiceCreateForm(forms.Form):
    participant = forms.ModelChoiceField(
        empty_label="Select participant",
        queryset=Participant.objects.all(),
    )
    period_start = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "dd/mm/yyyy"})
    )
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "dd/mm/yyyy"})
    )
    support_item = forms.ModelChoiceField(
        empty_label="Select support item",
        queryset=SupportItem.objects.filter(is_active=True).order_by("item_number"),
    )

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        if period_start and period_end and period_end < period_start:
            self.add_error("period_end", "Period end must be on or after period start.")
        return cleaned_data
```

- [ ] **Step 4: Add query helpers to `invoices/views.py`**

Update imports:

```python
from coordinators.models import CoordinationLog
from .forms import (
    InvoiceCreateForm,
    InvoiceSettingsForm,
    SupportCoordinationInvoiceCreateForm,
    TravelClaimForm,
)
```

Add after `get_billable_logs`:

```python
def get_billable_coordination_logs(participant, period_start, period_end):
    return CoordinationLog.objects.filter(
        participant=participant,
        service_date__gte=period_start,
        service_date__lte=period_end,
        status=CoordinationLog.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related("participant", "coordinator")


def get_selected_billable_coordination_logs(coordination_log_ids, require_single_participant=True):
    try:
        unique_ids = [
            int(coordination_log_id)
            for coordination_log_id in dict.fromkeys(coordination_log_ids)
        ]
    except (TypeError, ValueError):
        return [], "Selected coordination logs are no longer available for invoicing."

    coordination_logs = CoordinationLog.objects.filter(
        id__in=unique_ids,
        status=CoordinationLog.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related("participant", "coordinator")
    coordination_logs = list(coordination_logs.order_by("service_date", "id"))
    if len(coordination_logs) != len(unique_ids):
        return [], "Selected coordination logs are no longer available for invoicing."

    participant_ids = {log.participant_id for log in coordination_logs}
    if require_single_participant and len(participant_ids) > 1:
        return [], "Selected coordination logs must belong to one participant."
    return coordination_logs, ""
```

- [ ] **Step 5: Commit helper tests and form/query code**

```bash
git add invoices/forms.py invoices/views.py invoices/tests_invoices.py
git commit -m "feat: add support coordination invoice form helpers"
```

---

### Task 4: Build Dedicated SC Invoice Create Page

**Files:**
- Modify: `invoices/views.py`
- Modify: `invoices/urls.py`
- Create: `templates/invoices/support_coordination_invoice_form.html`
- Create: `templates/invoices/support_coordination_invoice_rows.html`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing create-flow tests**

Add to `InvoiceGenerationTests`:

```python
def test_admin_can_create_support_coordination_invoice(self):
    coordination_log = self.create_coordination_log(actual_hours=Decimal("1.50"))
    self.login_admin()

    response = self.client.post(
        reverse("support_coordination_invoice_create"),
        {
            "participant": self.participant.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-01",
            "support_item": self.support_item.id,
            "coordination_log_ids": [coordination_log.id],
        },
    )

    invoice = Invoice.objects.get()
    self.assertRedirects(response, reverse("invoice_detail", args=[invoice.id]))
    self.assertEqual(invoice.invoice_type, Invoice.InvoiceType.SUPPORT_COORDINATION)
    self.assertEqual(invoice.lines.count(), 1)
    line = invoice.lines.get()
    self.assertIsNone(line.service_log)
    self.assertEqual(line.coordination_log, coordination_log)
    coordination_log.refresh_from_db()
    self.assertEqual(coordination_log.status, CoordinationLog.Status.INVOICED)

def test_support_coordination_invoice_create_groups_selected_logs_by_participant(self):
    first_log = self.create_coordination_log(case_notes="First participant SC work.")
    other_log = self.create_coordination_log(
        participant=self.other_participant,
        case_notes="Other participant SC work.",
    )
    self.login_admin()

    response = self.client.get(
        reverse("support_coordination_invoice_create"),
        {"coordination_log_ids": [first_log.id, other_log.id]},
    )

    self.assertContains(response, 'class="invoice-selected-group"', count=2)
    self.assertContains(response, "Ava Nguyen")
    self.assertContains(response, "Ben Taylor")
    self.assertContains(response, "Create Invoice for Ava Nguyen")
    self.assertContains(response, "Create Invoice for Ben Taylor")
```

- [ ] **Step 2: Add URL**

In `invoices/urls.py`, import `support_coordination_invoice_create` and add:

```python
path(
    "invoices/support-coordination/new/",
    support_coordination_invoice_create,
    name="support_coordination_invoice_create",
),
```

- [ ] **Step 3: Add grouping helpers**

In `invoices/views.py`, add:

```python
def build_support_coordination_invoice_form_data(coordination_logs):
    return {
        "participant": coordination_logs[0].participant_id,
        "period_start": min(log.service_date for log in coordination_logs).isoformat(),
        "period_end": max(log.service_date for log in coordination_logs).isoformat(),
    }


def build_coordination_invoice_rows(coordination_logs):
    return [{"coordination_log": coordination_log} for coordination_log in coordination_logs]


def build_selected_coordination_invoice_groups(coordination_logs):
    groups = OrderedDict()
    ordered_logs = sorted(
        coordination_logs,
        key=lambda log: (
            log.participant.display_name,
            log.service_date,
            log.id,
        ),
    )
    for coordination_log in ordered_logs:
        group = groups.setdefault(
            coordination_log.participant_id,
            {
                "participant": coordination_log.participant,
                "coordination_logs": [],
            },
        )
        group["coordination_logs"].append(coordination_log)

    invoice_groups = []
    for group in groups.values():
        logs = group["coordination_logs"]
        period_start = min(log.service_date for log in logs)
        period_end = max(log.service_date for log in logs)
        period_label = format_au_date(period_start)
        if period_start != period_end:
            period_label = f"{period_label} - {format_au_date(period_end)}"
        invoice_groups.append(
            {
                "participant": group["participant"],
                "period_start": period_start,
                "period_end": period_end,
                "period_label": period_label,
                "total_hours": sum((log.actual_hours for log in logs), Decimal("0.00")),
                "count": len(logs),
                "selected_coordination_log_ids": [log.id for log in logs],
                "invoice_rows": build_coordination_invoice_rows(logs),
            }
        )
    return invoice_groups
```

- [ ] **Step 4: Add create view**

Add:

```python
@admin_required
def support_coordination_invoice_create(request):
    selected_ids = request.GET.getlist("coordination_log_ids")
    if request.method == "POST":
        selected_ids = request.POST.getlist("coordination_log_ids")
    selected_logs = []
    selected_error = ""
    active_selected_ids = selected_ids
    selected_invoice_groups = []

    if selected_ids:
        selected_logs, selected_error = get_selected_billable_coordination_logs(
            selected_ids,
            require_single_participant=request.method == "POST",
        )

    if (
        request.method == "GET"
        and selected_logs
        and len({log.participant_id for log in selected_logs}) == 1
    ):
        form = SupportCoordinationInvoiceCreateForm(
            build_support_coordination_invoice_form_data(selected_logs)
        )
        form.is_valid()
    elif request.method == "POST":
        form = SupportCoordinationInvoiceCreateForm(request.POST)
    elif request.method == "GET" and selected_logs:
        form = SupportCoordinationInvoiceCreateForm()
    else:
        form = SupportCoordinationInvoiceCreateForm(request.GET or None)

    coordination_logs = CoordinationLog.objects.none()
    if selected_error:
        active_selected_ids = []
        if request.method == "GET" and form.is_valid():
            selected_error = ""
            coordination_logs = get_billable_coordination_logs(
                form.cleaned_data["participant"],
                form.cleaned_data["period_start"],
                form.cleaned_data["period_end"],
            )
    elif selected_logs:
        coordination_logs = selected_logs
        if request.method == "GET":
            selected_invoice_groups = build_selected_coordination_invoice_groups(selected_logs)
    elif form.is_valid():
        coordination_logs = get_billable_coordination_logs(
            form.cleaned_data["participant"],
            form.cleaned_data["period_start"],
            form.cleaned_data["period_end"],
        )

    if request.method == "POST":
        if selected_error:
            coordination_logs = CoordinationLog.objects.none()
        elif form.is_valid():
            support_item = form.cleaned_data["support_item"]
            if selected_logs:
                coordination_logs = selected_logs
            else:
                coordination_logs = get_billable_coordination_logs(
                    form.cleaned_data["participant"],
                    form.cleaned_data["period_start"],
                    form.cleaned_data["period_end"],
                )
            coordination_logs = [
                log
                for log in coordination_logs
                if log.participant_id == form.cleaned_data["participant"].id
                and form.cleaned_data["period_start"]
                <= log.service_date
                <= form.cleaned_data["period_end"]
            ]
            if selected_logs and len(coordination_logs) != len(selected_logs):
                selected_error = (
                    "Selected coordination logs do not match the invoice participant and period."
                )
                coordination_logs = CoordinationLog.objects.none()
            elif not coordination_logs:
                messages.error(request, "No approved coordination logs found for this invoice.")
            else:
                with transaction.atomic():
                    invoice = Invoice.objects.create(
                        participant=form.cleaned_data["participant"],
                        period_start=form.cleaned_data["period_start"],
                        period_end=form.cleaned_data["period_end"],
                        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
                        created_by=request.user,
                    )
                    for coordination_log in coordination_logs:
                        InvoiceLine.objects.create_from_coordination_log(
                            invoice=invoice,
                            coordination_log=coordination_log,
                            support_item=support_item,
                        )
                        coordination_log.status = CoordinationLog.Status.INVOICED
                        coordination_log.save(update_fields=["status", "updated_at"])
                write_audit_log(
                    request.user,
                    AuditLog.Action.SUPPORT_COORDINATION_INVOICE_CREATED,
                    invoice,
                    f"Created support coordination invoice {invoice.invoice_number}.",
                )
                messages.success(request, "Support coordination invoice created.")
                return redirect(invoice)

    return render(
        request,
        "invoices/support_coordination_invoice_form.html",
        {
            "form": form,
            "coordination_logs": coordination_logs,
            "invoice_rows": build_coordination_invoice_rows(coordination_logs),
            "selected_invoice_groups": selected_invoice_groups,
            "selected_error": selected_error,
            "selected_coordination_log_ids": active_selected_ids,
        },
    )
```

- [ ] **Step 5: Add template**

Create `templates/invoices/support_coordination_invoice_form.html` based on `templates/invoices/invoice_form.html`, replacing service-specific labels with coordination-specific labels:

```django
{% extends "admin_base.html" %}

{% block title %}Create Support Coordination Invoice - Brisbane Star Care{% endblock %}

{% block content %}
<div class="page-header">
  <div>
    <h1>Create Support Coordination Invoice</h1>
    <p>Select approved coordination logs for one participant and period.</p>
  </div>
</div>

<form method="get" class="filter-bar invoice-preview-filter">
  {{ form.non_field_errors }}
  {% for coordination_log_id in selected_coordination_log_ids %}
    <input type="hidden" name="coordination_log_ids" value="{{ coordination_log_id }}">
  {% endfor %}
  <label>
    Participant
    {{ form.participant.errors }}
    {{ form.participant }}
  </label>
  <label>
    Period start
    {{ form.period_start.errors }}
    {{ form.period_start }}
  </label>
  <label>
    Period end
    {{ form.period_end.errors }}
    {{ form.period_end }}
  </label>
  <label>
    Support item
    {{ form.support_item.errors }}
    {{ form.support_item }}
  </label>
  <button type="submit">Preview Logs</button>
</form>

{% if selected_error %}
  <section class="card">
    <p>{{ selected_error }}</p>
  </section>
{% endif %}

<section class="card table-card invoice-preview-table">
  <h2>Approved Coordination Logs</h2>
  {% if selected_invoice_groups %}
    <div class="invoice-selected-groups">
      {% for group in selected_invoice_groups %}
        <article class="invoice-selected-group">
          <div class="invoice-selected-group-header">
            <div>
              <h3>{{ group.participant.display_name }}</h3>
              <p>{{ group.count }} log{{ group.count|pluralize }} | {{ group.period_label }} | {{ group.total_hours }} hours</p>
            </div>
          </div>
          <form method="post">
            {% csrf_token %}
            <input type="hidden" name="participant" value="{{ group.participant.id }}">
            <input type="hidden" name="period_start" value="{{ group.period_start|date:'Y-m-d' }}">
            <input type="hidden" name="period_end" value="{{ group.period_end|date:'Y-m-d' }}">
            {% for coordination_log_id in group.selected_coordination_log_ids %}
              <input type="hidden" name="coordination_log_ids" value="{{ coordination_log_id }}">
            {% endfor %}
            <label>
              Support item
              {{ form.support_item.errors }}
              {{ form.support_item }}
            </label>
            {% include "invoices/support_coordination_invoice_rows.html" with invoice_rows=group.invoice_rows %}
            <div class="invoice-preview-actions">
              <button type="submit">Create Invoice for {{ group.participant.display_name }}</button>
            </div>
          </form>
        </article>
      {% endfor %}
    </div>
  {% elif coordination_logs %}
    <form method="post">
      {% csrf_token %}
      <input type="hidden" name="participant" value="{{ form.cleaned_data.participant.id }}">
      <input type="hidden" name="period_start" value="{{ form.cleaned_data.period_start|date:'Y-m-d' }}">
      <input type="hidden" name="period_end" value="{{ form.cleaned_data.period_end|date:'Y-m-d' }}">
      <input type="hidden" name="support_item" value="{{ form.cleaned_data.support_item.id }}">
      {% for coordination_log_id in selected_coordination_log_ids %}
        <input type="hidden" name="coordination_log_ids" value="{{ coordination_log_id }}">
      {% endfor %}
      {% include "invoices/support_coordination_invoice_rows.html" with invoice_rows=invoice_rows %}
      <div class="invoice-preview-actions">
        <button type="submit">Create Support Coordination Invoice</button>
      </div>
    </form>
  {% else %}
    <div class="invoice-preview-empty-state empty-state">
      <strong>No approved coordination logs found</strong>
      <p>Choose another participant, date range, and support item, or approve submitted coordination logs before creating an invoice.</p>
    </div>
  {% endif %}
</section>
{% endblock %}
```

Create `templates/invoices/support_coordination_invoice_rows.html` with:

```django
<table>
  <thead>
    <tr>
      <th>Date</th>
      <th>Coordinator</th>
      <th>Coordination type</th>
      <th class="invoice-preview-hours-cell">Hours</th>
      <th>Notes</th>
    </tr>
  </thead>
  <tbody>
    {% for row in invoice_rows %}
      <tr>
        <td class="invoice-preview-date-cell">{{ row.coordination_log.service_date|date:"d/m/Y" }}</td>
        <td class="invoice-preview-worker-cell">{{ row.coordination_log.coordinator.display_name }}</td>
        <td class="invoice-preview-support-cell">{{ row.coordination_log.get_coordination_type_display }}</td>
        <td class="invoice-preview-hours-cell">{{ row.coordination_log.actual_hours }}</td>
        <td class="invoice-preview-notes-cell">{{ row.coordination_log.case_notes|truncatechars:80 }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
```

- [ ] **Step 6: Run focused create-flow tests**

Run:

```bash
python manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_preview_shows_approved_uninvoiced_logs invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_create_requires_admin invoices.tests_invoices.InvoiceGenerationTests.test_admin_can_create_support_coordination_invoice invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_create_groups_selected_logs_by_participant
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit create page**

```bash
git add invoices/views.py invoices/urls.py invoices/forms.py templates/invoices/support_coordination_invoice_form.html templates/invoices/support_coordination_invoice_rows.html invoices/tests_invoices.py
git commit -m "feat: add support coordination invoice create page"
```

---

### Task 5: Add Coordination Logs Billing Action

**Files:**
- Modify: `templates/coordinators/coordination_log_list.html`
- Modify: `coordinators/tests.py`

- [ ] **Step 1: Write failing list-page test**

Add to `CoordinationLogAdminReviewTests`:

```python
def test_coordination_log_list_shows_invoice_selection_for_approved_logs_only(self):
    approved_log = self.log
    approved_log.status = CoordinationLog.Status.APPROVED
    approved_log.save(update_fields=["status", "updated_at"])
    submitted_log = CoordinationLog.objects.create(
        participant=self.participant,
        coordinator=self.coordinator,
        service_date=date(2026, 9, 5),
        start_time=time(9, 0),
        end_time=time(10, 0),
        break_minutes=0,
        actual_hours=Decimal("1.00"),
        coordination_type=CoordinationLog.CoordinationType.GENERAL,
        case_notes="Submitted work.",
    )

    response = self.client.get(reverse("coordination_log_list"))

    self.assertContains(response, "Create SC Invoice from Selected")
    self.assertContains(response, f'name="coordination_log_ids" value="{approved_log.id}"')
    self.assertNotContains(response, f'name="coordination_log_ids" value="{submitted_log.id}"')
```

- [ ] **Step 2: Add billing action form**

In `templates/coordinators/coordination_log_list.html`, wrap the table with:

```django
<form method="get" action="{% url 'support_coordination_invoice_create' %}">
```

Add a billing action header above the table:

```django
<div class="service-log-billing-action">
  <div>
    <strong>Billing action</strong>
    <span>Select approved coordination logs to create a support coordination invoice.</span>
  </div>
  <button type="submit">Create SC Invoice from Selected</button>
</div>
```

Add a `Select` column before Date and render checkboxes only for approved logs without invoice lines:

```django
<th>Select</th>
```

```django
<td>
  {% if log.status == "approved" and not log.invoice_lines.exists %}
    <input type="checkbox" name="coordination_log_ids" value="{{ log.id }}">
  {% endif %}
</td>
```

Update empty-row colspan by one.

- [ ] **Step 3: Run list-page test**

Run:

```bash
python manage.py test coordinators.tests.CoordinationLogAdminReviewTests.test_coordination_log_list_shows_invoice_selection_for_approved_logs_only
```

Expected: pass.

- [ ] **Step 4: Commit billing action**

```bash
git add templates/coordinators/coordination_log_list.html coordinators/tests.py
git commit -m "feat: add coordination log invoice selection action"
```

---

### Task 6: Display Invoice Type In List And Detail

**Files:**
- Modify: `templates/invoices/invoice_list.html`
- Modify: `templates/invoices/invoice_detail.html`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing display tests**

Add:

```python
def test_invoice_list_shows_support_coordination_type_label(self):
    invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        created_by=self.admin_user,
    )
    self.login_admin()

    response = self.client.get(reverse("invoice_placeholder"))

    self.assertContains(response, invoice.invoice_number)
    self.assertContains(response, "Support Coordination")

def test_invoice_detail_shows_invoice_type(self):
    invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        created_by=self.admin_user,
    )
    self.login_admin()

    response = self.client.get(reverse("invoice_detail", args=[invoice.id]))

    self.assertContains(response, "Invoice type")
    self.assertContains(response, "Support Coordination")
```

- [ ] **Step 2: Update templates**

In `templates/invoices/invoice_list.html`, add below the invoice number stack:

```django
<span class="status-pill status-{{ invoice.invoice_type }}">{{ invoice.get_invoice_type_display }}</span>
```

In `templates/invoices/invoice_detail.html`, add to the first detail list:

```django
<dt>Invoice type</dt><dd><span class="status-pill status-{{ invoice.invoice_type }}">{{ invoice.get_invoice_type_display }}</span></dd>
```

- [ ] **Step 3: Run display tests**

Run:

```bash
python manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_invoice_list_shows_support_coordination_type_label invoices.tests_invoices.InvoiceGenerationTests.test_invoice_detail_shows_invoice_type
```

Expected: pass.

- [ ] **Step 4: Commit type display**

```bash
git add templates/invoices/invoice_list.html templates/invoices/invoice_detail.html invoices/tests_invoices.py
git commit -m "feat: show invoice type in admin invoices"
```

---

### Task 7: Update CSV And PDF For SC Invoice Sources

**Files:**
- Modify: `invoices/views.py`
- Modify: `invoices/tests_exports.py`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing export tests**

Add tests that create an SC invoice and assert:

```python
self.assertIn('filename="SC_Invoice_', response["Content-Disposition"])
self.assertContains(response, "support_coordination")
```

For PDF, assert:

```python
self.assertEqual(response["Content-Type"], "application/pdf")
self.assertIn('filename="SC_Invoice_', response["Content-Disposition"])
self.assertIn(b"Support Coordination", response.content)
```

- [ ] **Step 2: Add source helper functions**

In `invoices/views.py`, replace `invoice_line_service_date` with:

```python
def invoice_line_source_date(line):
    if line.service_log_id:
        return format_au_date(line.service_log.service_date)
    if line.coordination_log_id:
        return format_au_date(line.coordination_log.service_date)
    return "-"
```

Update PDF line rendering to call `invoice_line_source_date(line)`.

Change line prefetch/selects to include both sources:

```python
invoice_lines = list(invoice.lines.select_related("service_log", "coordination_log"))
```

- [ ] **Step 3: Update filename helper**

Change `invoice_download_filename`:

```python
prefix = "SC_Invoice" if invoice.invoice_type == Invoice.InvoiceType.SUPPORT_COORDINATION else "Invoice"
return f"{prefix}_{invoice_date}_{invoice_sequence}_{participant_name}.{extension}"
```

- [ ] **Step 4: Update CSV**

Add `invoice_type` to CSV header and rows:

```python
"invoice_type",
```

Row value:

```python
invoice.invoice_type,
```

Use `invoice_download_filename(invoice, "csv")` for CSV disposition.

- [ ] **Step 5: Update PDF header**

After invoice date in the PDF header, add:

```python
pdf_text(
    f"Invoice Type: {invoice.get_invoice_type_display()}",
    invoice_detail_x,
    invoice_detail_y - (detail_line_gap * 3),
    8.5,
),
```

- [ ] **Step 6: Run export tests**

Run:

```bash
python manage.py test invoices.tests_exports invoices.tests_invoices.InvoiceGenerationTests
```

Expected: all invoice export and invoice generation tests pass.

- [ ] **Step 7: Commit export changes**

```bash
git add invoices/views.py invoices/tests_exports.py invoices/tests_invoices.py
git commit -m "feat: support coordination invoice exports"
```

---

### Task 8: Release SC Logs On Cancel/Delete And Add Audit Action

**Files:**
- Modify: `core/models.py`
- Create migration: `core/migrations/0004_alter_auditlog_action.py`
- Modify: `invoices/views.py`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing release and audit tests**

Add:

```python
def test_cancelling_support_coordination_invoice_releases_coordination_logs(self):
    coordination_log = self.create_coordination_log(status=CoordinationLog.Status.INVOICED)
    invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 1),
        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        created_by=self.admin_user,
    )
    InvoiceLine.objects.create_from_coordination_log(invoice, coordination_log, self.support_item)
    self.login_admin()

    response = self.client.post(reverse("invoice_cancel", args=[invoice.id]))

    coordination_log.refresh_from_db()
    self.assertRedirects(response, reverse("invoice_detail", args=[invoice.id]))
    self.assertEqual(coordination_log.status, CoordinationLog.Status.APPROVED)

def test_deleting_draft_support_coordination_invoice_releases_coordination_logs(self):
    coordination_log = self.create_coordination_log(status=CoordinationLog.Status.INVOICED)
    invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 1),
        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
        created_by=self.admin_user,
    )
    InvoiceLine.objects.create_from_coordination_log(invoice, coordination_log, self.support_item)
    self.login_admin()

    response = self.client.post(reverse("invoice_delete", args=[invoice.id]))

    coordination_log.refresh_from_db()
    self.assertRedirects(response, reverse("invoice_placeholder"))
    self.assertEqual(coordination_log.status, CoordinationLog.Status.APPROVED)

def test_support_coordination_invoice_creation_writes_audit_log(self):
    coordination_log = self.create_coordination_log()
    self.login_admin()

    self.client.post(
        reverse("support_coordination_invoice_create"),
        {
            "participant": self.participant.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-01",
            "support_item": self.support_item.id,
            "coordination_log_ids": [coordination_log.id],
        },
    )

    invoice = Invoice.objects.get()
    audit = AuditLog.objects.get(action=AuditLog.Action.SUPPORT_COORDINATION_INVOICE_CREATED)
    self.assertEqual(audit.object_id, str(invoice.id))
    self.assertIn(invoice.invoice_number, audit.summary)
```

- [ ] **Step 2: Add audit action**

In `core/models.py`, add:

```python
SUPPORT_COORDINATION_INVOICE_CREATED = (
    "support_coordination_invoice_created",
    "Support coordination invoice created",
)
```

Run:

```bash
python manage.py makemigrations core
```

- [ ] **Step 3: Update release helper**

Replace `release_invoice_service_logs` with:

```python
def release_invoice_source_logs(invoice):
    service_logs = {
        line.service_log_id: line.service_log
        for line in invoice.lines.select_related("service_log")
        if line.service_log_id
    }
    for service_log in service_logs.values():
        service_log.status = ServiceLog.Status.APPROVED
        service_log.save(update_fields=["status", "updated_at"])

    coordination_logs = {
        line.coordination_log_id: line.coordination_log
        for line in invoice.lines.select_related("coordination_log")
        if line.coordination_log_id
    }
    for coordination_log in coordination_logs.values():
        coordination_log.status = CoordinationLog.Status.APPROVED
        coordination_log.save(update_fields=["status", "updated_at"])

    invoice.lines.all().delete()
```

Update cancel/delete calls:

```python
release_invoice_source_logs(invoice)
```

- [ ] **Step 4: Run release/audit tests**

Run:

```bash
python manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_cancelling_support_coordination_invoice_releases_coordination_logs invoices.tests_invoices.InvoiceGenerationTests.test_deleting_draft_support_coordination_invoice_releases_coordination_logs invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_creation_writes_audit_log
```

Expected: pass.

- [ ] **Step 5: Commit release/audit behavior**

```bash
git add core/models.py core/migrations/0004_alter_auditlog_action.py invoices/views.py invoices/tests_invoices.py
git commit -m "feat: release support coordination logs from invoices"
```

---

### Task 9: Final Verification And PR

**Files:**
- No required source edits unless tests reveal issues.

- [ ] **Step 1: Run migrations check**

Run:

```bash
python manage.py makemigrations --check --dry-run
```

Expected:

- `No changes detected`

- [ ] **Step 2: Run all tests**

Run:

```bash
python manage.py test
```

Expected:

- All tests pass.

- [ ] **Step 3: Run code diff check**

Run:

```bash
git diff --check
```

Expected:

- No output.

- [ ] **Step 4: Manual smoke test locally**

Use the browser or Django test client flow:

1. Admin creates or opens an SC.
2. Admin assigns participant to SC.
3. SC submits a coordination log.
4. Admin approves the coordination log.
5. Admin selects it from Coordination Logs.
6. Admin creates Support Coordination invoice.
7. Admin downloads PDF and CSV.
8. Confirm existing Support Worker service invoice flow still creates and downloads.

- [ ] **Step 5: Commit any final polish**

If verification requires small fixes to the support coordination invoice workflow:

```bash
git add invoices/models.py invoices/views.py invoices/forms.py invoices/urls.py templates/invoices/support_coordination_invoice_form.html templates/invoices/support_coordination_invoice_rows.html templates/invoices/invoice_list.html templates/invoices/invoice_detail.html templates/coordinators/coordination_log_list.html core/models.py invoices/tests_invoices.py invoices/tests_exports.py coordinators/tests.py
git commit -m "fix: polish support coordination invoice workflow"
```

- [ ] **Step 6: Push branch and open PR**

```bash
git push -u origin codex/sc-invoice-design
gh pr create --title "Add support coordination invoice workflow" --body-file pr-body.md
```

PR body should include:

```markdown
## Summary
- Add Admin-only Support Coordination invoice creation from approved coordination logs.
- Keep SC invoice sources separate from Support Worker service-log invoices.
- Add SC invoice PDF/CSV filename and invoice type labeling.

## Safety Notes
- SC users do not receive invoice access.
- Support Worker invoice behavior remains unchanged.
- Service logs and coordination logs cannot be mixed in one invoice.

## Test Plan
- python manage.py test
- python manage.py makemigrations --check --dry-run
- git diff --check
```
