# SC Invoice List Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split Support Coordination invoices into a dedicated Admin list page while keeping existing service invoice behavior and invoice core logic intact.

**Architecture:** Reuse the existing `invoice_list` rendering path with an explicit invoice type mode. The existing `/invoices/` page becomes service-invoice-only, and a new `/invoices/support-coordination/` page becomes SC-invoice-only. Detail, PDF, CSV, status changes, cancel/delete, and creation flows continue to use the existing shared invoice functions.

**Tech Stack:** Django views, URL routing, Django templates, existing test suite with `.venv\Scripts\python.exe manage.py test`.

---

## File Structure

- Modify `invoices/views.py`: add a small list-mode helper and route-specific wrappers for service invoices and SC invoices.
- Modify `invoices/urls.py`: add the `support_coordination_invoice_list` route before invoice detail routes.
- Modify `templates/invoices/invoice_list.html`: make headings, helper copy, reset links, create button, and empty state mode-aware.
- Modify `templates/admin_base.html`: add `SC Invoices` under the `Coordination` section and keep active states accurate.
- Modify `invoices/tests_invoices.py`: cover service/SC list separation and access rules.

---

### Task 1: Add Route-Level List Separation Tests

**Files:**
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Add failing tests for list separation**

Add tests in `InvoiceGenerationTests` near the existing invoice list tests:

```python
def test_service_invoice_list_excludes_support_coordination_invoices(self):
    service_log = self.create_service_log()
    service_invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        created_by=self.accountant_user,
    )
    InvoiceLine.objects.create_from_service_log(service_invoice, service_log)
    coordination_invoice, _ = self.create_support_coordination_invoice()
    self.login_admin()

    response = self.client.get(reverse("invoice_placeholder"))

    self.assertContains(response, service_invoice.invoice_number)
    self.assertNotContains(response, coordination_invoice.invoice_number)
    self.assertContains(response, "Invoices")
    self.assertContains(response, "Manage service invoices.")


def test_support_coordination_invoice_list_shows_only_sc_invoices(self):
    service_log = self.create_service_log()
    service_invoice = Invoice.objects.create(
        participant=self.participant,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        created_by=self.accountant_user,
    )
    InvoiceLine.objects.create_from_service_log(service_invoice, service_log)
    coordination_invoice, _ = self.create_support_coordination_invoice()
    self.login_admin()

    response = self.client.get(reverse("support_coordination_invoice_list"))

    self.assertContains(response, coordination_invoice.invoice_number)
    self.assertNotContains(response, service_invoice.invoice_number)
    self.assertContains(response, "SC Invoices")
    self.assertContains(response, "Manage support coordination invoices.")
    self.assertContains(response, reverse("support_coordination_invoice_create"))


def test_accountant_cannot_access_support_coordination_invoice_list(self):
    self.login_accountant()

    response = self.client.get(reverse("support_coordination_invoice_list"))

    self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.venv\Scripts\python.exe manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_service_invoice_list_excludes_support_coordination_invoices invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_list_shows_only_sc_invoices invoices.tests_invoices.InvoiceGenerationTests.test_accountant_cannot_access_support_coordination_invoice_list
```

Expected: fail because `support_coordination_invoice_list` does not exist yet and `/invoices/` still includes both invoice types.

- [ ] **Step 3: Commit tests**

Run:

```powershell
git add invoices/tests_invoices.py
git commit -m "test: cover SC invoice list separation"
```

---

### Task 2: Add Service and SC Invoice List Modes

**Files:**
- Modify: `invoices/views.py`
- Modify: `invoices/urls.py`

- [ ] **Step 1: Refactor `invoice_list` into a typed list helper**

In `invoices/views.py`, keep the existing `invoice_list` name for `/invoices/`, and add:

```python
def invoice_list_for_type(request, invoice_type, page_title, page_description, create_url_name=None):
    visible_invoices = invoice_queryset_for_user(request.user).filter(invoice_type=invoice_type)
    status_counts = {
        row["status"]: row["count"]
        for row in visible_invoices.values("status").annotate(count=Count("id"))
    }
    # Preserve the existing filtering, sorting, pagination, and render context.
```

Then update the existing `invoice_list` view to call:

```python
@finance_required
def invoice_list(request):
    return invoice_list_for_type(
        request,
        Invoice.InvoiceType.SERVICE,
        "Invoices",
        "Manage service invoices.",
    )
```

Add the SC list view:

```python
@admin_required
def support_coordination_invoice_list(request):
    return invoice_list_for_type(
        request,
        Invoice.InvoiceType.SUPPORT_COORDINATION,
        "SC Invoices",
        "Manage support coordination invoices.",
        create_url_name="support_coordination_invoice_create",
    )
```

Important implementation details:
- Keep `invoice_queryset_for_user()` unchanged so accountant detail/export protection still works.
- Inside `invoice_list_for_type`, status overview URLs should point to the active list route:
  - service mode: `reverse("invoice_placeholder")`
  - SC mode: `reverse("support_coordination_invoice_list")`
- Pass `page_title`, `page_description`, `create_url_name`, and `list_url_name` into the template.

- [ ] **Step 2: Register the new URL route**

In `invoices/urls.py`, import `support_coordination_invoice_list` and add this route before `<int:invoice_id>` routes:

```python
path(
    "invoices/support-coordination/",
    support_coordination_invoice_list,
    name="support_coordination_invoice_list",
),
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_service_invoice_list_excludes_support_coordination_invoices invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_list_shows_only_sc_invoices invoices.tests_invoices.InvoiceGenerationTests.test_accountant_cannot_access_support_coordination_invoice_list
```

Expected: list mode tests pass after the template is updated in Task 3; URL access test should pass now.

- [ ] **Step 4: Commit view and URL changes**

Run:

```powershell
git add invoices/views.py invoices/urls.py
git commit -m "feat: add SC invoice list route"
```

---

### Task 3: Update Admin Navigation and List Template Copy

**Files:**
- Modify: `templates/admin_base.html`
- Modify: `templates/invoices/invoice_list.html`
- Modify: `invoices/tests_invoices.py`

- [ ] **Step 1: Update invoice list template to use mode-aware copy**

In `templates/invoices/invoice_list.html`:
- Replace hard-coded `<h1>Invoices</h1>` with `{{ page_title }}`.
- Replace hard-coded subtitle with `{{ page_description }}`.
- Keep the existing table and row actions unchanged.
- Change reset and clear-filter links to use `list_url_name`:

```django
<a class="button secondary" href="{% url list_url_name %}">Reset</a>
```

- Add an optional create button in the page header:

```django
{% if create_url_name %}
  <a class="button" href="{% url create_url_name %}">Create SC Invoice</a>
{% endif %}
```

- [ ] **Step 2: Add sidebar link**

In `templates/admin_base.html`, under `Coordination`, add:

```django
<a class="sidebar-link{% if request.resolver_match.url_name == 'support_coordination_invoice_list' or request.resolver_match.url_name == 'support_coordination_invoice_create' %} active{% endif %}" href="{% url 'support_coordination_invoice_list' %}">SC Invoices</a>
```

Remove `support_coordination_invoice_create` from the normal `Invoices` active-state condition if it is present there, so creating SC invoices highlights the Coordination section instead of Business invoices.

- [ ] **Step 3: Add sidebar active-state test**

Add:

```python
def test_support_coordination_invoice_list_highlights_sc_invoice_sidebar_link(self):
    self.login_admin()

    response = self.client.get(reverse("support_coordination_invoice_list"))

    self.assertContains(
        response,
        f'class="sidebar-link active" href="{reverse("support_coordination_invoice_list")}"',
    )
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe manage.py test invoices.tests_invoices.InvoiceGenerationTests.test_service_invoice_list_excludes_support_coordination_invoices invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_list_shows_only_sc_invoices invoices.tests_invoices.InvoiceGenerationTests.test_accountant_cannot_access_support_coordination_invoice_list invoices.tests_invoices.InvoiceGenerationTests.test_support_coordination_invoice_list_highlights_sc_invoice_sidebar_link
```

Expected: all pass.

- [ ] **Step 5: Commit template changes**

Run:

```powershell
git add templates/admin_base.html templates/invoices/invoice_list.html invoices/tests_invoices.py
git commit -m "feat: separate SC invoice admin navigation"
```

---

### Task 4: Regression Verification

**Files:**
- No code changes expected.

- [ ] **Step 1: Run invoice tests**

Run:

```powershell
.venv\Scripts\python.exe manage.py test invoices.tests_invoices invoices.tests_exports
```

Expected: all invoice tests pass.

- [ ] **Step 2: Run migration check**

Run:

```powershell
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Expected: `No changes detected`.

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output.

- [ ] **Step 4: Run full test suite**

Run:

```powershell
.venv\Scripts\python.exe manage.py test
```

Expected: all tests pass.

---

## Self-Review

Spec coverage:
- The plan keeps the model and invoice core behavior unchanged.
- The plan separates the service invoice list and SC invoice list through typed list routes.
- The plan adds Admin sidebar navigation under Coordination.
- The plan keeps accountant access limited to service invoices.
- The plan includes focused and full regression tests.

Placeholder scan:
- No unresolved placeholders or open-ended implementation instructions remain.

Type consistency:
- Uses existing `Invoice.InvoiceType.SERVICE` and `Invoice.InvoiceType.SUPPORT_COORDINATION`.
- Uses existing URL name `support_coordination_invoice_create`.
- Adds new URL name `support_coordination_invoice_list`.
