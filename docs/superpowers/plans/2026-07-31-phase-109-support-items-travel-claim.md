# Phase 109 Support Items and Travel Claim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three verified 2026-27 NDIS Support Items and let finance users enter a final provider travel non-labour amount per approved Service Log when creating an invoice.

**Architecture:** A versioned, idempotent management command owns the three verified Support Items. The existing Service Log `kilometres` field remains worker-entered source data; travel money exists only as a typed Invoice Line created by finance staff. `InvoiceLine.service_log` becomes a foreign key with a `(service_log, line_type)` uniqueness constraint so one log can safely produce a service line and an optional travel line.

**Tech Stack:** Django 5, Django forms and ORM, SQLite/PostgreSQL migrations, Django TestCase, existing server-rendered templates and CSS.

---

## File Map

- Create `scheduling/management/__init__.py`: management package marker.
- Create `scheduling/management/commands/__init__.py`: command package marker.
- Create `scheduling/management/commands/seed_ndis_support_items_2026_27.py`: exact three-item seed/update command.
- Create `scheduling/tests_support_item_seed.py`: command tests.
- Modify `invoices/models.py`: typed service/travel lines and travel-line factory.
- Create `invoices/migrations/0003_invoiceline_line_type_and_relation.py`: preserve existing lines while changing the relation.
- Modify `invoices/forms.py`: one travel amount form per approved Service Log.
- Modify `invoices/views.py`: validate travel claims and create all invoice lines transactionally.
- Modify `templates/invoices/invoice_form.html`: show worker kilometres and admin travel amount.
- Modify `static/css/app.css`: compact responsive travel input styling.
- Modify `invoices/tests_invoices.py`: model, validation, transaction, and HTML contract coverage.
- Modify `invoices/tests_exports.py`: PDF/CSV travel-line coverage.

### Task 1: Seed the three verified Support Items

**Files:**
- Create: `scheduling/management/__init__.py`
- Create: `scheduling/management/commands/__init__.py`
- Create: `scheduling/management/commands/seed_ndis_support_items_2026_27.py`
- Create: `scheduling/tests_support_item_seed.py`

- [ ] **Step 1: Write failing command tests**

Create tests that run the command and assert all three exact records:

```python
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from scheduling.models import SupportItem


class NdisSupportItemSeedTests(TestCase):
    def test_command_creates_verified_2026_27_items(self):
        call_command("seed_ndis_support_items_2026_27")

        self.assertEqual(SupportItem.objects.count(), 3)
        self.assertEqual(
            SupportItem.objects.get(item_number="01_011_0107_1_1").price_limit,
            Decimal("73.58"),
        )
        self.assertEqual(
            SupportItem.objects.get(item_number="04_104_0125_6_1").unit,
            SupportItem.Unit.HOUR,
        )
        travel = SupportItem.objects.get(item_number="04_799_0125_6_1")
        self.assertEqual(travel.unit, SupportItem.Unit.EACH)
        self.assertEqual(travel.price_limit, Decimal("1.00"))
        self.assertEqual(travel.gst_code, SupportItem.GSTCode.GST_FREE)
        self.assertTrue(travel.is_active)

    def test_command_is_idempotent_and_preserves_unrelated_items(self):
        unrelated = SupportItem.objects.create(
            item_number="LOCAL-ITEM",
            name="Local item",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("10.00"),
        )

        call_command("seed_ndis_support_items_2026_27")
        call_command("seed_ndis_support_items_2026_27")

        self.assertEqual(
            SupportItem.objects.filter(item_number="01_011_0107_1_1").count(),
            1,
        )
        unrelated.refresh_from_db()
        self.assertEqual(unrelated.price_limit, Decimal("10.00"))
```

- [ ] **Step 2: Run tests and verify the command is missing**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test scheduling.tests_support_item_seed
```

Expected: error containing `Unknown command: 'seed_ndis_support_items_2026_27'`.

- [ ] **Step 3: Implement the idempotent command**

Implement:

```python
from decimal import Decimal

from django.core.management.base import BaseCommand

from scheduling.models import SupportItem


ITEMS = (
    {
        "item_number": "01_011_0107_1_1",
        "name": "Assistance With Self-Care Activities - Standard - Weekday Daytime",
        "category": "Core Supports",
        "unit": SupportItem.Unit.HOUR,
        "price_limit": Decimal("73.58"),
        "gst_code": SupportItem.GSTCode.GST_FREE,
        "is_active": True,
        "notes": "2026-27 NDIS Pricing Schedule v1.2. National price.",
    },
    {
        "item_number": "04_104_0125_6_1",
        "name": "Access Community Social and Rec Activ - Standard - Weekday Daytime",
        "category": "Core Supports",
        "unit": SupportItem.Unit.HOUR,
        "price_limit": Decimal("73.58"),
        "gst_code": SupportItem.GSTCode.GST_FREE,
        "is_active": True,
        "notes": "2026-27 NDIS Pricing Schedule v1.2. National price.",
    },
    {
        "item_number": "04_799_0125_6_1",
        "name": "Provider travel - non-labour costs",
        "category": "Core Supports",
        "unit": SupportItem.Unit.EACH,
        "price_limit": Decimal("1.00"),
        "gst_code": SupportItem.GSTCode.GST_FREE,
        "is_active": True,
        "notes": (
            "2026-27 NDIS Pricing Schedule v1.2. Each at $1.00 is a "
            "claim-value mechanism. Do not automatically convert worker "
            "kilometres into a claim amount."
        ),
    },
)


class Command(BaseCommand):
    help = "Create or update the three verified 2026-27 NDIS support items."

    def handle(self, *args, **options):
        for item in ITEMS:
            item_number = item["item_number"]
            defaults = {key: value for key, value in item.items() if key != "item_number"}
            SupportItem.objects.update_or_create(
                item_number=item_number,
                defaults=defaults,
            )
        self.stdout.write(self.style.SUCCESS("2026-27 NDIS support items ready: 3."))
```

Create empty `__init__.py` files in both new management-package directories.

- [ ] **Step 4: Run the seed tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test scheduling.tests_support_item_seed
```

Expected: all tests pass.

- [ ] **Step 5: Commit Phase 109A**

```powershell
git add scheduling/management scheduling/tests_support_item_seed.py
git commit -m "feat: seed 2026-27 NDIS support items"
```

### Task 2: Allow typed service and travel lines per Service Log

**Files:**
- Modify: `invoices/models.py`
- Create: `invoices/migrations/0003_invoiceline_line_type_and_relation.py`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing model tests**

First extend the existing test helpers so later tests are self-contained:

```python
# Add this beside the existing actual_hours override:
kilometres = overrides.pop("kilometres", Decimal("0.00"))

# Replace the fixed value in ServiceLog.objects.create_from_shift():
kilometres=kilometres,

def create_invoice(self):
    return Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        created_by=self.accountant_user,
    )

def create_travel_item(self, **overrides):
    defaults = {
        "name": "Provider travel - non-labour costs",
        "category": "Core Supports",
        "unit": SupportItem.Unit.EACH,
        "price_limit": Decimal("1.00"),
        "gst_code": SupportItem.GSTCode.GST_FREE,
        "is_active": True,
    }
    defaults.update(overrides)
    return SupportItem.objects.create(
        item_number="04_799_0125_6_1",
        **defaults,
    )
```

Then add tests proving one Service Log can create two typed lines and duplicate types are rejected:

```python
from django.db import IntegrityError, transaction

def test_service_log_can_have_service_and_travel_lines(self):
    service_log = self.create_service_log(actual_hours=Decimal("2.00"))
    invoice = self.create_invoice()
    travel_item = self.create_travel_item()

    service_line = InvoiceLine.objects.create_from_service_log(invoice, service_log)
    travel_line = InvoiceLine.objects.create_travel_from_service_log(
        invoice=invoice,
        service_log=service_log,
        amount=Decimal("35.00"),
        support_item=travel_item,
    )

    self.assertEqual(service_line.line_type, InvoiceLine.LineType.SERVICE)
    self.assertEqual(travel_line.line_type, InvoiceLine.LineType.TRAVEL_NON_LABOUR)
    self.assertEqual(travel_line.quantity, Decimal("35.00"))
    self.assertEqual(travel_line.unit_price, Decimal("1.00"))
    self.assertEqual(travel_line.line_total, Decimal("35.00"))
    self.assertEqual(service_log.invoice_lines.count(), 2)

def test_service_log_rejects_duplicate_line_type(self):
    service_log = self.create_service_log()
    invoice = self.create_invoice()
    InvoiceLine.objects.create_from_service_log(invoice, service_log)

    with self.assertRaises(IntegrityError), transaction.atomic():
        InvoiceLine.objects.create_from_service_log(invoice, service_log)
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_service_log_can_have_service_and_travel_lines invoices.tests_invoices.InvoiceGenerationTests.test_service_log_rejects_duplicate_line_type
```

Expected: failures because `LineType`, `invoice_lines`, and `create_travel_from_service_log` do not exist.

- [ ] **Step 3: Implement the model change**

In `InvoiceLine` add:

```python
class LineType(models.TextChoices):
    SERVICE = "service", "Service"
    TRAVEL_NON_LABOUR = "travel_non_labour", "Provider travel - non-labour"

line_type = models.CharField(
    max_length=30,
    choices=LineType.choices,
    default=LineType.SERVICE,
)

service_log = models.ForeignKey(
    ServiceLog,
    on_delete=models.PROTECT,
    related_name="invoice_lines",
)
```

Add:

```python
constraints = [
    models.UniqueConstraint(
        fields=["service_log", "line_type"],
        name="unique_invoice_line_type_per_service_log",
    ),
]
```

Make `create_from_service_log()` explicitly set `line_type=SERVICE`. Add `create_travel_from_service_log()` that requires a positive amount and creates a snapshot from support item `04_799_0125_6_1`, with quantity equal to the amount and `$1.00` unit price.

- [ ] **Step 4: Generate and inspect the migration**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations invoices
.\.venv\Scripts\python.exe manage.py sqlmigrate invoices 0003
```

Expected: migration adds `line_type`, changes the relation to `ForeignKey`, and adds the uniqueness constraint. Existing rows receive the default `service`.

- [ ] **Step 5: Update existing reverse-relation queries**

Replace billable filters:

```python
invoice_line__isnull=True
```

with:

```python
invoice_lines__isnull=True
```

Update tests and application references from `service_log.invoice_line` to `service_log.invoice_lines`. Keep direct `InvoiceLine.objects.filter(service_log=...)` calls unchanged.

- [ ] **Step 6: Run model and invoice regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices
```

Expected: all tests pass.

- [ ] **Step 7: Commit the typed-line model**

```powershell
git add invoices/models.py invoices/migrations invoices/tests_invoices.py invoices/views.py
git commit -m "feat: support typed invoice lines"
```

### Task 3: Validate admin-entered travel claims

**Files:**
- Modify: `invoices/forms.py`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing travel form tests**

Add tests for blank, valid, invalid, and zero-kilometre claims:

```python
def test_travel_claim_form_accepts_blank_or_positive_money(self):
    log = self.create_service_log(kilometres=Decimal("43.00"))
    blank = TravelClaimForm({}, service_log=log, prefix=f"travel-{log.id}")
    valid = TravelClaimForm(
        {f"travel-{log.id}-amount": "35.00"},
        service_log=log,
        prefix=f"travel-{log.id}",
    )

    self.assertTrue(blank.is_valid())
    self.assertTrue(valid.is_valid())
    self.assertEqual(valid.cleaned_data["amount"], Decimal("35.00"))

def test_travel_claim_form_rejects_amount_without_recorded_kilometres(self):
    log = self.create_service_log(kilometres=Decimal("0.00"))
    form = TravelClaimForm(
        {f"travel-{log.id}-amount": "10.00"},
        service_log=log,
        prefix=f"travel-{log.id}",
    )

    self.assertFalse(form.is_valid())
    self.assertIn("amount", form.errors)
```

- [ ] **Step 2: Run tests and verify `TravelClaimForm` is missing**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices
```

Expected: import or name failure for `TravelClaimForm`.

- [ ] **Step 3: Implement `TravelClaimForm`**

Add:

```python
class TravelClaimForm(forms.Form):
    amount = forms.DecimalField(
        required=False,
        min_value=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        label="Travel claim amount",
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )

    def __init__(self, *args, service_log, **kwargs):
        self.service_log = service_log
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and self.service_log.kilometres <= 0:
            raise forms.ValidationError(
                "A travel claim requires worker-recorded kilometres."
            )
        return amount or Decimal("0.00")
```

- [ ] **Step 4: Run form tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices
```

Expected: all tests pass.

- [ ] **Step 5: Commit travel validation**

```powershell
git add invoices/forms.py invoices/tests_invoices.py
git commit -m "feat: validate invoice travel claims"
```

### Task 4: Create invoices transactionally with optional travel lines

**Files:**
- Modify: `invoices/views.py`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing creation tests**

Cover these behaviours:

```python
def test_invoice_create_adds_admin_approved_travel_line(self):
    log = self.create_service_log(kilometres=Decimal("43.00"))
    self.create_travel_item()
    self.login_accountant()
    payload = self.create_payload()
    payload[f"travel-{log.id}-amount"] = "35.00"

    response = self.client.post(reverse("invoice_create"), payload)

    invoice = Invoice.objects.get()
    self.assertRedirects(response, invoice.get_absolute_url())
    travel = invoice.lines.get(line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR)
    self.assertEqual(travel.quantity, Decimal("35.00"))
    self.assertEqual(travel.line_total, Decimal("35.00"))
    log.refresh_from_db()
    self.assertEqual(log.kilometres, Decimal("43.00"))

def test_blank_travel_claim_keeps_existing_invoice_flow(self):
    log = self.create_service_log(kilometres=Decimal("43.00"))
    self.login_accountant()

    self.client.post(reverse("invoice_create"), self.create_payload())

    invoice = Invoice.objects.get()
    self.assertEqual(invoice.lines.count(), 1)
    self.assertFalse(
        invoice.lines.filter(
            line_type=InvoiceLine.LineType.TRAVEL_NON_LABOUR
        ).exists()
    )

def test_missing_travel_item_creates_no_partial_invoice(self):
    log = self.create_service_log(kilometres=Decimal("43.00"))
    self.login_accountant()
    payload = self.create_payload()
    payload[f"travel-{log.id}-amount"] = "35.00"

    response = self.client.post(reverse("invoice_create"), payload)

    self.assertEqual(response.status_code, 200)
    self.assertEqual(Invoice.objects.count(), 0)
    log.refresh_from_db()
    self.assertEqual(log.status, ServiceLog.Status.APPROVED)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices
```

Expected: travel input is ignored and no travel line is created.

- [ ] **Step 3: Build and validate per-log travel forms**

Add a helper returning rows:

```python
def build_invoice_rows(service_logs, data=None):
    return [
        {
            "service_log": service_log,
            "travel_form": TravelClaimForm(
                data,
                service_log=service_log,
                prefix=f"travel-{service_log.id}",
            ),
        }
        for service_log in service_logs
    ]
```

On POST, call `is_valid()` for every row before creating the invoice. Collect positive amounts by Service Log ID.

- [ ] **Step 4: Add atomic invoice creation**

Wrap Invoice, service lines, optional travel lines, and Service Log status changes in `transaction.atomic()`.

Before entering the transaction, when any amount is positive, require:

```python
SupportItem.objects.filter(
    item_number="04_799_0125_6_1",
    is_active=True,
).first()
```

If absent, render the form with:

```text
Provider travel support item 04_799_0125_6_1 is missing or inactive.
```

Do not create an Invoice or update Service Log statuses.

- [ ] **Step 5: Deduplicate released Service Logs**

Change `release_invoice_service_logs()` to restore each source Service Log once even when the invoice contains two lines:

```python
service_logs = {
    line.service_log_id: line.service_log
    for line in invoice.lines.select_related("service_log")
}
for service_log in service_logs.values():
    service_log.status = ServiceLog.Status.APPROVED
    service_log.save(update_fields=["status", "updated_at"])
```

- [ ] **Step 6: Run invoice tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices
```

Expected: all tests pass.

- [ ] **Step 7: Commit transactional creation**

```powershell
git add invoices/views.py invoices/tests_invoices.py
git commit -m "feat: add travel claims to invoice creation"
```

### Task 5: Show kilometres and travel amount on Create Invoice

**Files:**
- Modify: `templates/invoices/invoice_form.html`
- Modify: `static/css/app.css`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Write failing template contract tests**

```python
def test_invoice_preview_shows_worker_kilometres_and_travel_input(self):
    log = self.create_service_log(kilometres=Decimal("43.00"))
    self.login_accountant()

    response = self.client.get(reverse("invoice_create"), self.create_payload())

    self.assertContains(response, "43.00 km")
    self.assertContains(response, f'name="travel-{log.id}-amount"')
    self.assertContains(response, "Travel claim amount")
    self.assertContains(response, "Admin enters the approved amount")
```

- [ ] **Step 2: Run the test and verify the UI is missing**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_invoice_preview_shows_worker_kilometres_and_travel_input
```

Expected: failure because kilometres and travel input are absent.

- [ ] **Step 3: Move the POST form around the approved-log table**

Render `invoice_rows` instead of bare `service_logs`. Add columns:

```html
<th>Travel km</th>
<th>Travel claim amount</th>
```

For each row:

```html
<td>{{ row.service_log.kilometres|floatformat:2 }} km</td>
<td class="invoice-travel-claim">
  {% if row.service_log.kilometres > 0 %}
    {{ row.travel_form.amount.errors }}
    {{ row.travel_form.amount }}
    <small>Admin enters the approved amount.</small>
  {% else %}
    <span class="muted">No travel recorded</span>
  {% endif %}
</td>
```

Keep all existing hidden participant, period, and selected Service Log fields inside the POST form.

- [ ] **Step 4: Add focused responsive CSS**

Add only scoped rules:

```css
.invoice-travel-claim input {
  width: 8rem;
}

.invoice-travel-claim small {
  display: block;
  margin-top: 0.25rem;
  color: var(--color-text-muted);
}
```

Keep the existing `.invoice-preview-table` internal horizontal scrolling behaviour.

- [ ] **Step 5: Run template and theme tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices core.tests_theme
```

Expected: all tests pass.

- [ ] **Step 6: Commit the UI**

```powershell
git add templates/invoices/invoice_form.html static/css/app.css invoices/tests_invoices.py
git commit -m "feat: show travel claims in invoice preview"
```

### Task 6: Verify PDF, CSV, deletion, and cancellation

**Files:**
- Modify: `invoices/tests_exports.py`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Add export tests using a travel line**

Create a travel line with quantity `$35.00` and assert:

```python
self.assertIn("04_799_0125_6_1", pdf_content)
self.assertIn("Provider travel - non-labour costs", pdf_content)
self.assertIn("35.00", pdf_content)
self.assertIn("$1.00", pdf_content)
self.assertIn("$35.00", pdf_content)
```

For CSV, assert the travel row has:

```python
{
    "support_item_number": "04_799_0125_6_1",
    "unit": "each",
    "quantity": "35.00",
    "unit_price": "1.00",
    "line_total": "35.00",
}
```

- [ ] **Step 2: Add release-flow regression tests**

Create service and travel lines from one Service Log, then delete a draft invoice and cancel another invoice. Assert the Service Log returns to `APPROVED` exactly once and both lines are removed according to existing rules.

- [ ] **Step 3: Run export and invoice tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_exports invoices.tests_invoices
```

Expected: all tests pass.

- [ ] **Step 4: Commit export coverage**

```powershell
git add invoices/tests_exports.py invoices/tests_invoices.py
git commit -m "test: cover invoice travel exports and release"
```

### Task 7: Full verification and handoff

**Files:**
- Verify all modified files.

- [ ] **Step 1: Check migrations**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations --check
.\.venv\Scripts\python.exe manage.py migrate
```

Expected: no pending migrations; migration succeeds.

- [ ] **Step 2: Run focused suites**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test scheduling.tests_support_items scheduling.tests_support_item_seed service_logs invoices.tests_invoices invoices.tests_exports
```

Expected: all tests pass.

- [ ] **Step 3: Run project checks and full test suite**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Expected: system check reports no issues and all tests pass.

- [ ] **Step 4: Run the seed command locally and inspect records**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py seed_ndis_support_items_2026_27
.\.venv\Scripts\python.exe manage.py shell -c "from scheduling.models import SupportItem; print(list(SupportItem.objects.filter(item_number__in=['01_011_0107_1_1','04_104_0125_6_1','04_799_0125_6_1']).values_list('item_number','unit','price_limit')))"
```

Expected: all three records are shown with `$73.58`, `$73.58`, and `$1.00`.

- [ ] **Step 5: Browser smoke test**

Verify:

- Support Items lists all three new records.
- Worker Service Log still accepts kilometres and no money field.
- Create Invoice shows the recorded kilometres.
- Blank Travel amount creates only a service line.
- Positive Travel amount creates service and Travel lines.
- Invoice detail, CSV, and PDF show the Travel line.
- Draft invoice deletion restores the source Service Log.
- Desktop and 390px widths have no body horizontal overflow.

- [ ] **Step 6: Final commit if verification caused tracked changes**

```powershell
git add scheduling invoices templates/invoices/invoice_form.html static/css/app.css
git commit -m "feat: complete provider travel invoice workflow"
```

- [ ] **Step 7: Push and prepare PR details**

Push branch `codex/phase-109-support-items-travel-claim`. Provide the user with a PR link, title, description, exact local browser tests, and the Render Shell command:

```bash
python manage.py seed_ndis_support_items_2026_27
```
