# Phase 124 Invoice PDF Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate readable multi-page invoice PDFs when line items exceed one page, while preserving the approved single-page design and all invoice business behaviour.

**Architecture:** Extend the hand-built PDF writer so it can serialize multiple independent page streams that share the existing fonts. Add small invoice-layout helpers that render repeated line-item headers and calculate row heights, then paginate complete rows before they cross the printable bottom boundary. Render Invoice Total and Payment Details once on the final page.

**Tech Stack:** Django 5, Python standard library PDF serialization, Django `TestCase`, Poppler visual rendering.

---

### Task 1: Reproduce the overflow with a failing export test

**Files:**
- Modify: `invoices/tests_exports.py`

- [ ] **Step 1: Extend the service-log fixture helper**

Allow `create_invoiced_service_log` to accept a `service_date` so one invoice can contain several unique logs:

```python
def create_invoiced_service_log(self, service_date=date(2026, 6, 1)):
    shift = Shift.objects.create(
        # existing fields unchanged
        service_date=service_date,
    )
```

- [ ] **Step 2: Write the failing pagination test**

Create seven additional service logs and invoice lines, request the PDF, and assert the output has multiple page objects, repeated table headers, one Total, one Payment Details section, and each row date exactly once:

```python
def test_invoice_pdf_paginates_many_line_items_without_repeating_footer(self):
    for day in range(2, 9):
        service_log = self.create_invoiced_service_log(date(2026, 6, day))
        InvoiceLine.objects.create_from_service_log(self.invoice, service_log)
    self.login_accountant()

    response = self.client.get(reverse("invoice_pdf", args=[self.invoice.id]))
    content = response.content.decode("latin-1")

    self.assertGreater(content.count("/Type /Page /Parent"), 1)
    self.assertGreater(content.count("(Date) Tj"), 1)
    self.assertEqual(content.count("(Invoice Total) Tj"), 1)
    self.assertEqual(content.count("(Payment Details) Tj"), 1)
    for day in range(1, 9):
        self.assertEqual(content.count(f"({day:02d}/06/2026) Tj"), 1)
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_exports.InvoiceExportTests.test_invoice_pdf_paginates_many_line_items_without_repeating_footer --verbosity 2
```

Expected: FAIL because the current builder emits one `/Type /Page /Parent` object.

### Task 2: Add multi-page support to the lightweight PDF builder

**Files:**
- Modify: `invoices/views.py`
- Test: `invoices/tests_exports.py`

- [ ] **Step 1: Extract page-stream rendering**

Move the existing operation and image collection loop into:

```python
def build_pdf_page_stream(lines):
    operations = []
    images = []
    # preserve current text, line, and image rendering logic
    return "\n".join(operations).encode("latin-1", errors="replace"), images
```

- [ ] **Step 2: Normalize single-page and multi-page input**

Keep existing callers compatible:

```python
def normalize_pdf_pages(lines_or_pages):
    if lines_or_pages and isinstance(lines_or_pages[0], list):
        return lines_or_pages
    return [lines_or_pages]
```

- [ ] **Step 3: Serialize one page object per page stream**

Update `build_simple_pdf` to allocate shared font objects plus Page, Contents, and image objects for every page. `/Pages /Kids` must list all page object references and `/Count` must equal the page count.

- [ ] **Step 4: Run the focused test**

Expected: it still fails on invoice pagination because `invoice_pdf` still sends a single page, while all existing short-PDF tests remain green.

### Task 3: Paginate complete invoice line rows

**Files:**
- Modify: `invoices/views.py`
- Test: `invoices/tests_exports.py`

- [ ] **Step 1: Add reusable table-header and row-height helpers**

```python
def invoice_line_row_height(description_lines):
    return max(30, 20 + (len(description_lines) * 10))

def append_invoice_table_header(page_lines, table_top, columns, continued=False):
    # append heading, column labels, and divider using existing styles
    return table_top - 76
```

- [ ] **Step 2: Add a compact continuation-page header**

Continuation pages identify the invoice and participant, draw the purple divider, and repeat the line-item header without repeating the full business and participant blocks.

- [ ] **Step 3: Paginate before rendering a row**

Collect pages in `pdf_pages`. Before each complete row, compare its calculated height with the printable bottom boundary. If it would cross the boundary, append a continuation page and render the row there.

For the final row, also reserve enough space for Total and Payment Details. If the final row plus footer does not fit, move that row to a new page so the footer can follow it naturally.

- [ ] **Step 4: Render the footer once on the final page**

Calculate `footer_top` from the final row position without the old fixed-position overlap. Keep the existing Total and two-column Payment Details design.

- [ ] **Step 5: Pass all pages to the builder**

```python
response = HttpResponse(build_simple_pdf(pdf_pages), content_type="application/pdf")
```

- [ ] **Step 6: Run the focused pagination test and verify GREEN**

Expected: PASS with at least two pages, repeated headers, one Total, one Payment Details section, and each service date once.

### Task 4: Regression and visual verification

**Files:**
- Modify only if a verified defect remains: `invoices/views.py`, `invoices/tests_exports.py`

- [ ] **Step 1: Run invoice export tests**

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_exports --verbosity 1
```

Expected: all tests pass.

- [ ] **Step 2: Run invoice workflow tests**

```powershell
.\.venv\Scripts\python.exe manage.py test invoices.tests_invoices --verbosity 1
```

Expected: all tests pass.

- [ ] **Step 3: Run Django system checks**

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Expected: `System check identified no issues`.

- [ ] **Step 4: Generate short and multi-line test PDFs**

Use the existing test fixtures or local demo invoice data to save representative responses under the system temporary directory. Do not alter production or Render data.

- [ ] **Step 5: Render every generated page with Poppler**

```powershell
pdftoppm -png -r 140 <input.pdf> <output-prefix>
```

Verify that table rows do not split or overlap, continuation headers are clear, the single-page design remains unchanged, and Total and Payment Details appear once on the final page.

- [ ] **Step 6: Commit implementation**

```powershell
git add -- invoices/views.py invoices/tests_exports.py
git commit -m "fix: paginate multi-line invoice pdfs"
```
