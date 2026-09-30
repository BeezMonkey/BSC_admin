# Cancellation Service Log Invoicing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make approved participant cancellation charges selectable from the Service Logs Approved billing workbench and combinable with selected service logs in one invoice without exposing cancellation metadata on customer-facing output.

**Architecture:** Keep `ParticipantCancellation` and `ServiceLog` as separate sources. Query billable cancellation records alongside the existing Service Logs Approved view, submit them as `participant_cancellation_ids`, and extend the existing invoice selection/grouping pipeline to validate and combine both source types. Existing manual participant/date invoice creation and PDF rendering remain unchanged.

**Tech Stack:** Django views/templates/models, Django TestCase, existing CSS design tokens.

---

### Task 1: Show billable cancellation charges in the Approved workbench

**Files:**
- Modify: `service_logs/tests_review.py`
- Modify: `service_logs/views.py`
- Modify: `templates/service_logs/service_log_list.html`
- Modify: `static/css/app.css`

- [ ] **Step 1: Write failing workbench tests**

Add tests that create `ParticipantCancellation` records and assert that the Approved view contains `name="participant_cancellation_ids"`, `Approved cancellation charges`, and `Approved rostered charge`.

Cover pending, waived, rejected, out-of-range, wrong-participant, and already-invoiced records as excluded cases. Assert the section is absent outside the Approved status card.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
& "C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe" manage.py test service_logs.tests_review.ServiceLogReviewTests
```

Expected: FAIL because the Service Logs view does not expose `billable_cancellations` and the template has no cancellation checkbox section.

- [ ] **Step 3: Add the filtered cancellation queryset**

Import `ParticipantCancellation` in `service_logs/views.py`. When `status == ServiceLog.Status.APPROVED`, query approved cancellations with `invoice_lines__isnull=True`, apply the same selected participant and resolved `shift__service_date` bounds, and select the related shift, participant, worker, and support item. For every other status, return `ParticipantCancellation.objects.none()`.

- [ ] **Step 4: Render the compact admin-only section**

Inside the existing invoice-selection form, add a section headed `Approved cancellation charges`. Render one checkbox named `participant_cancellation_ids` per record with service date, participant, worker, Approved status, rostered hours, and `Approved rostered charge`. Do not render cancellation type, reason, details, claim code, or review note.

Add narrowly scoped responsive CSS for the heading and compact table without changing the existing Service Logs table behaviour.

- [ ] **Step 5: Run the workbench tests and verify GREEN**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add service_logs/tests_review.py service_logs/views.py templates/service_logs/service_log_list.html static/css/app.css
git commit -m "feat: show approved cancellation charges for billing"
```

### Task 2: Validate selected cancellations in invoice creation

**Files:**
- Modify: `invoices/tests_cancellations.py`
- Modify: `invoices/views.py`
- Modify: `templates/invoices/invoice_form.html`

- [ ] **Step 1: Write failing selection tests**

Add cancellation-only and combined same-participant selection tests. GET must preserve `participant_cancellation_ids`; POST must create one Service Log line and one Participant Cancellation line when both are selected. Add stale, non-approved, already-invoiced, wrong-participant, and out-of-period rejection tests.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
& "C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe" manage.py test invoices.tests_cancellations.ParticipantCancellationInvoiceTests
```

Expected: FAIL because `invoice_create` currently ignores `participant_cancellation_ids` whenever selected Service Log IDs are present.

- [ ] **Step 3: Add selected cancellation validation**

Implement `get_selected_billable_cancellations(ids, require_single_participant=True)` beside `get_selected_billable_logs()`. It must parse unique integer IDs, require Approved status and no invoice line, select related shift objects, verify all IDs survived, and enforce the participant rule.

Read `participant_cancellation_ids` from GET and POST. Combine participant IDs from both record types when enforcing the single-participant POST rule. Derive form participant and period from the earliest/latest selected date across both types.

- [ ] **Step 4: Preserve IDs and create selected invoice lines**

Pass `selected_participant_cancellation_ids` to the template. Add hidden inputs to the filter form, selected preview form, and final POST form. When explicit IDs are present, use only validated selected cancellations; do not automatically add other approved cancellations in the period.

On POST, validate that every selected record belongs to the form participant and period before entering the transaction. Create cancellation invoice lines with `create_from_participant_cancellation()` in the same transaction as Service Log lines.

- [ ] **Step 5: Run the cancellation invoice tests and verify GREEN**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add invoices/tests_cancellations.py invoices/views.py templates/invoices/invoice_form.html
git commit -m "feat: invoice selected cancellation charges"
```

### Task 3: Support mixed and multi-participant preview groups

**Files:**
- Modify: `invoices/tests_cancellations.py`
- Modify: `invoices/views.py`
- Modify: `templates/invoices/invoice_form.html`

- [ ] **Step 1: Write failing grouping tests**

Create selected service logs and cancellation charges for two participants. Assert GET renders one preview group per participant, each group carries only its own hidden IDs, the period covers both record types, total hours include actual and rostered hours, and cancellation-only groups are valid.

- [ ] **Step 2: Run the grouping tests and verify RED**

Run the Task 2 test command. Expected: FAIL because `build_selected_invoice_groups()` accepts only Service Logs and assumes every preview row has `row.service_log`.

- [ ] **Step 3: Generalize selected invoice groups**

Change `build_selected_invoice_groups(service_logs, participant_cancellations)` to group both types by participant. Store separate source lists and call `build_invoice_rows()` to obtain date-sorted rows. Calculate count and total hours across both sources and expose both hidden-ID collections.

- [ ] **Step 4: Render mixed rows safely**

Update the selected-group table body to use the same source conditional already used by the single-participant preview. Service rows keep travel controls; cancellation rows show the normal support item, rostered hours, no travel claim, and `Approved rostered charge`.

- [ ] **Step 5: Run grouping and full invoice tests**

Run:

```powershell
& "C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe" manage.py test invoices
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add invoices/tests_cancellations.py invoices/views.py templates/invoices/invoice_form.html
git commit -m "feat: group mixed billing selections"
```

### Task 4: Regression, privacy, and visual verification

**Files:**
- Modify only if a regression is found in a file already in scope.

- [ ] **Step 1: Run all affected application tests**

```powershell
& "C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe" manage.py test service_logs scheduling.tests_cancellations invoices core.tests_theme.ThemeTokenTests.test_service_log_invoice_filter_layout_assets_exist
```

Expected: all tests pass with zero failures.

- [ ] **Step 2: Run Django and diff checks**

```powershell
& "C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe" manage.py check
git diff --check
```

Expected: no issues and no whitespace errors.

- [ ] **Step 3: Verify the customer-facing privacy boundary**

Run the existing PDF cancellation test and confirm output still contains the normal support item but not `CANC`, `Short notice`, or private cancellation details.

- [ ] **Step 4: Run the local server and inspect the workflow**

Open the Service Logs Approved view with demo records. Verify desktop and 760px layouts, apply participant/date filters, select a Service Log plus a cancellation charge, preview the invoice, and confirm both rows appear without overlap.

- [ ] **Step 5: Commit any scoped verification fixes**

If visual verification requires a scoped correction, commit only files already in scope with message `style: polish mixed billing selection`.
