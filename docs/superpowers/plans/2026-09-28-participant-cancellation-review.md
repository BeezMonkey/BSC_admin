# Participant Cancellation Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an assigned support worker report a participant cancellation, let an admin approve or reject it, and make approved charges invoiceable from the original rostered hours without changing normal service-log behavior.

**Architecture:** Add a one-to-one `ParticipantCancellation` workflow record owned by scheduling. Worker and admin views mutate that record and the linked shift state. Service invoices accept either approved `ServiceLog` sources or approved cancellation sources; invoice lines retain a typed source reference while the current Plan Manager PDF continues to render the ordinary support-item description.

**Tech Stack:** Django models, forms, function-based views, templates, CSS, SQLite/PostgreSQL-compatible migrations, Django `TestCase`.

---

## File structure

- `scheduling/models.py`: cancellation workflow model and shift review status.
- `scheduling/forms.py`: compact worker submission and admin review forms.
- `scheduling/views.py`, `scheduling/urls.py`: worker report and admin review endpoints.
- `templates/scheduling/worker_shift_detail.html`: worker entry point and review state.
- `templates/scheduling/participant_cancellation_form.html`: worker cancellation form.
- `templates/scheduling/participant_cancellation_list.html`: admin queue.
- `templates/scheduling/participant_cancellation_detail.html`: admin decision page.
- `templates/admin_base.html`: admin queue navigation.
- `invoices/models.py`, `invoices/views.py`, `templates/invoices/invoice_form.html`: invoiceable cancellation source and mixed invoice preview.
- `core/models.py`: cancellation audit actions.
- `static/css/app.css`, `static/css/admin.css`: compact states and forms using existing tokens.
- `scheduling/tests_cancellations.py`: workflow and permissions.
- `invoices/tests_cancellations.py`: invoice integration and PDF non-disclosure.

### Task 1: Cancellation domain model

**Files:**
- Modify: `scheduling/models.py`
- Modify: `core/models.py`
- Create: `scheduling/migrations/0005_participantcancellation_alter_shift_status.py`
- Create: `core/migrations/0007_alter_auditlog_action.py`
- Test: `scheduling/tests_cancellations.py`

- [x] **Step 1: Write failing model tests**

Cover one record per shift, allowed choice values, captured previous shift status,
planned-hours access through the shift, and the `CANC` internal claim type:

```python
def test_shift_accepts_only_one_participant_cancellation(self):
    ParticipantCancellation.objects.create(
        shift=self.shift,
        cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
        reason=ParticipantCancellation.Reason.OTHER,
        details="Participant cancelled by phone.",
        received_at=timezone.now(),
        previous_shift_status=Shift.Status.CONFIRMED,
        submitted_by=self.worker_user,
    )
    with self.assertRaises(IntegrityError):
        ParticipantCancellation.objects.create(
            shift=self.shift,
            cancellation_type=ParticipantCancellation.CancellationType.NO_SHOW,
            reason=ParticipantCancellation.Reason.OTHER,
            details="Duplicate.",
            received_at=timezone.now(),
            previous_shift_status=Shift.Status.CONFIRMED,
            submitted_by=self.worker_user,
        )
```

- [x] **Step 2: Run the model test and verify it fails**

Run: `python manage.py test scheduling.tests_cancellations.ParticipantCancellationModelTests`

Expected: failure because `ParticipantCancellation` does not exist.

- [x] **Step 3: Add the minimal model and audit choices**

Implement a one-to-one shift relation and these explicit choices:

```python
class ParticipantCancellation(models.Model):
    class CancellationType(models.TextChoices):
        SHORT_NOTICE = "short_notice", "Short notice cancellation"
        NO_SHOW = "no_show", "No show"

    class Reason(models.TextChoices):
        HEALTH = "health", "Health"
        FAMILY = "family", "Family issue"
        TRANSPORT = "transport", "Transport unavailable"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved and chargeable"
        WAIVED = "waived", "Charge waived"
        REJECTED = "rejected", "Rejected"
        INVOICED = "invoiced", "Invoiced"

    CLAIM_TYPE = "CANC"
```

Add submitter/reviewer timestamps and notes. Add
`Shift.Status.CANCELLATION_REVIEW`, include it in worker-visible and active
conflict statuses, and add audit actions for submit, approve, waive, and reject.

- [x] **Step 4: Generate migrations and run model tests**

Run:

```powershell
python manage.py makemigrations scheduling core
python manage.py test scheduling.tests_cancellations.ParticipantCancellationModelTests
```

Expected: migrations created and model tests pass.

- [x] **Step 5: Commit the domain model**

```powershell
git add scheduling/models.py scheduling/migrations core/models.py core/migrations scheduling/tests_cancellations.py
git commit -m "feat: add participant cancellation records"
```

### Task 2: Worker cancellation report

**Files:**
- Modify: `scheduling/forms.py`
- Modify: `scheduling/views.py`
- Modify: `scheduling/urls.py`
- Modify: `service_logs/views.py`
- Modify: `templates/scheduling/worker_shift_detail.html`
- Create: `templates/scheduling/participant_cancellation_form.html`
- Test: `scheduling/tests_cancellations.py`

- [x] **Step 1: Write failing worker-flow tests**

Test that only the assigned worker can report a published or confirmed scheduled
shift, details are required, submission stores the original status and moves the
shift to cancellation review, duplicates are blocked, and service-log creation
returns 404 while review is pending.

```python
def test_assigned_worker_submits_participant_cancellation(self):
    self.client.force_login(self.worker_user)
    response = self.client.post(
        reverse("worker_participant_cancellation_create", args=[self.shift.id]),
        {
            "cancellation_type": "short_notice",
            "reason": "health",
            "details": "Participant called to cancel.",
            "received_at": "2026-09-28T08:30",
        },
    )
    self.assertEqual(response.status_code, 302)
    self.shift.refresh_from_db()
    self.assertEqual(self.shift.status, Shift.Status.CANCELLATION_REVIEW)
```

- [x] **Step 2: Run worker-flow tests and verify failure**

Run: `python manage.py test scheduling.tests_cancellations.WorkerCancellationFlowTests`

Expected: missing URL/view/form failures.

- [x] **Step 3: Implement the compact worker flow**

Use a `ModelForm` exposing only cancellation type, reason, details, and received
time. Save the cancellation and shift status in one transaction. Query the shift
by the logged-in worker and valid source/status, and reject any shift with an
existing service log or cancellation. Add one secondary button and replace the
completion action with a pending-review message after submission.

- [x] **Step 4: Run worker and existing service-log tests**

Run:

```powershell
python manage.py test scheduling.tests_cancellations.WorkerCancellationFlowTests service_logs.tests_service_logs
```

Expected: all tests pass; normal scheduled and unscheduled service logs remain unchanged.

- [x] **Step 5: Commit the worker flow**

```powershell
git add scheduling/forms.py scheduling/views.py scheduling/urls.py service_logs/views.py templates/scheduling
git commit -m "feat: let workers report participant cancellations"
```

### Task 3: Admin cancellation review

**Files:**
- Modify: `scheduling/views.py`
- Modify: `scheduling/urls.py`
- Modify: `templates/admin_base.html`
- Create: `templates/scheduling/participant_cancellation_list.html`
- Create: `templates/scheduling/participant_cancellation_detail.html`
- Test: `scheduling/tests_cancellations.py`

- [x] **Step 1: Write failing admin-review tests**

Cover the pending queue, admin-only permissions, approve-and-charge, waive,
reject, reviewer/timestamp fields, shift transitions, and audit entries.

```python
def test_admin_approves_chargeable_cancellation(self):
    self.client.force_login(self.admin_user)
    response = self.client.post(
        reverse("participant_cancellation_approve", args=[self.cancellation.id]),
        {"admin_note": "Service agreement checked."},
    )
    self.assertRedirects(response, reverse("participant_cancellation_list"))
    self.cancellation.refresh_from_db()
    self.assertEqual(self.cancellation.status, ParticipantCancellation.Status.APPROVED)
    self.assertEqual(self.cancellation.shift.status, Shift.Status.CANCELLED)
```

- [x] **Step 2: Run admin-review tests and verify failure**

Run: `python manage.py test scheduling.tests_cancellations.AdminCancellationReviewTests`

Expected: missing review endpoints and templates.

- [x] **Step 3: Implement queue and three decisions**

List pending first, then recent reviewed records. Use POST-only decision endpoints
inside transactions. Approve and waive set the shift to cancelled; reject restores
`previous_shift_status`. Render the original shift and worker submission in a
compact review card, with no eligibility wizard or attachments.

- [x] **Step 4: Run admin-review and shift regression tests**

Run:

```powershell
python manage.py test scheduling.tests_cancellations.AdminCancellationReviewTests scheduling.tests_shifts
```

Expected: all tests pass.

- [x] **Step 5: Commit the admin review**

```powershell
git add scheduling/views.py scheduling/urls.py templates/admin_base.html templates/scheduling scheduling/tests_cancellations.py
git commit -m "feat: add admin cancellation review"
```

### Task 4: Invoice approved cancellations

**Files:**
- Modify: `invoices/models.py`
- Modify: `invoices/views.py`
- Modify: `templates/invoices/invoice_form.html`
- Create: `invoices/migrations/0005_invoiceline_participant_cancellation.py`
- Create: `invoices/tests_cancellations.py`
- Test: `invoices/tests_invoices.py`
- Test: `invoices/tests_exports.py`

- [x] **Step 1: Write failing invoice integration tests**

Test that approved cancellations appear for the participant/date range, use the
shift planned hours and original support-item rate, can be invoiced only once,
are linked only once, become billable again when a draft/issued invoice is cancelled,
and keep cancellation wording and `CANC` out of the PDF content.

```python
def test_approved_cancellation_uses_rostered_quantity_and_rate(self):
    line = InvoiceLine.objects.create_from_participant_cancellation(
        invoice=self.invoice,
        cancellation=self.cancellation,
    )
    self.assertEqual(line.quantity, self.shift.planned_hours)
    self.assertEqual(line.unit_price, self.shift.support_item.price_limit)
    self.assertEqual(line.description, self.shift.support_item.name)
    self.assertEqual(line.line_type, InvoiceLine.LineType.CANCELLATION)
```

- [x] **Step 2: Run invoice cancellation tests and verify failure**

Run: `python manage.py test invoices.tests_cancellations`

Expected: missing invoice source and manager method.

- [x] **Step 3: Add the typed invoice source**

Add a nullable `participant_cancellation` foreign key, a cancellation line type,
a conditional unique constraint, and expand the exactly-one-source constraint.
Implement `create_from_participant_cancellation()` with the shift support item and
planned hours. Keep `description=support_item.name`, so existing PDF rendering is
unchanged.

- [x] **Step 4: Extend invoice selection and release behavior**

Load approved, uninvoiced cancellations alongside approved service logs for the
same participant and period. Render a compact preview row without travel inputs.
Create both source types atomically. The unique invoice-line source marks a
cancellation as invoiced; deleting those lines makes it billable again.

- [x] **Step 5: Run invoice and export tests**

Run:

```powershell
python manage.py test invoices.tests_cancellations invoices.tests_invoices invoices.tests_exports
```

Expected: all tests pass, including assertions that Plan Manager PDF text contains
the ordinary support-item description but not `CANC`, `Short notice`, or the
private cancellation details.

- [ ] **Step 6: Commit invoice integration**

```powershell
git add invoices/models.py invoices/views.py invoices/migrations templates/invoices/invoice_form.html invoices/tests_cancellations.py invoices/tests_invoices.py invoices/tests_exports.py
git commit -m "feat: invoice approved participant cancellations"
```

### Task 5: Polish and full verification

**Files:**
- Modify: `static/css/app.css`
- Modify: `static/css/admin.css`
- Modify: relevant template tests if required

- [ ] **Step 1: Add style-contract assertions**

Assert that the worker report button/form and admin review cards use existing
button, field, status-pill, card, and responsive patterns rather than introducing
a parallel design system.

- [ ] **Step 2: Add minimal responsive styling**

Keep the worker form single-column on mobile and at most two columns on desktop.
Keep the admin decision buttons in the existing action row and avoid nested cards.

- [ ] **Step 3: Run the focused feature suite**

Run:

```powershell
python manage.py test scheduling.tests_cancellations service_logs.tests_service_logs invoices.tests_cancellations invoices.tests_invoices invoices.tests_exports core.tests_theme
```

Expected: all new tests pass; document any unchanged pre-existing theme assertion.

- [ ] **Step 4: Run framework and migration checks**

Run:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

Expected: no system issues, no uncommitted migrations, and no whitespace errors.

- [ ] **Step 5: Perform browser checks**

Verify worker report, worker pending state, admin queue, all three decisions,
invoice preview, and PDF output at desktop and 390px mobile widths. Confirm a
normal completed shift still follows the existing Service Log path.

- [ ] **Step 6: Commit final polish**

```powershell
git add static/css/app.css static/css/admin.css templates scheduling/tests_cancellations.py invoices/tests_cancellations.py
git commit -m "test: verify participant cancellation workflow"
```
