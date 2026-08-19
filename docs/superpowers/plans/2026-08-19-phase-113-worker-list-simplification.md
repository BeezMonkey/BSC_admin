# Phase 113 Worker List Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove inline compliance information from the Support Workers list while preserving compliance data and presentation on worker detail and edit pages.

**Architecture:** Keep the existing worker query, filters, permissions, and models unchanged. Add a focused rendering contract test, then make the minimum template-only change by removing the list header and row cell and correcting the empty-state column span.

**Tech Stack:** Django templates, Django `TestCase`, Python, HTML

---

### Task 1: Simplify the Support Workers table

**Files:**
- Modify: `workers/tests.py`
- Modify: `templates/workers/worker_list.html`

- [ ] **Step 1: Write the failing list/detail rendering test**

Add this test to `SupportWorkerManagementTests` in `workers/tests.py`:

```python
def test_worker_list_omits_compliance_summary_but_detail_retains_it(self):
    user = get_user_model().objects.create_user(
        username="maya",
        email="maya@example.com",
        password="test-password-123",
    )
    worker = SupportWorker.objects.create(
        user=user,
        first_name="Maya",
        last_name="Singh",
        email="maya@example.com",
        status=SupportWorker.Status.ACTIVE,
        police_check_status=SupportWorker.ComplianceStatus.CURRENT,
        wwcc_status=SupportWorker.ComplianceStatus.PENDING,
    )
    self.login_admin()

    list_response = self.client.get(reverse("worker_list"))
    detail_response = self.client.get(reverse("worker_detail", args=[worker.id]))

    self.assertNotContains(list_response, "<th>Compliance</th>", html=True)
    self.assertNotContains(list_response, "Police: Current")
    self.assertNotContains(list_response, "WWCC: Pending")
    self.assertContains(detail_response, "<h2>Compliance</h2>", html=True)
    self.assertContains(detail_response, "Police check")
    self.assertContains(detail_response, "WWCC / Blue Card")
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test workers.tests.SupportWorkerManagementTests.test_worker_list_omits_compliance_summary_but_detail_retains_it
```

Expected: `FAIL` because the current list still contains the Compliance header and inline Police/WWCC text.

- [ ] **Step 3: Apply the minimal template change**

In `templates/workers/worker_list.html`:

1. Remove the header:

```html
<th>Compliance</th>
```

2. Remove the row cell:

```html
<td>
  Police: {{ worker.get_police_check_status_display }}<br>
  WWCC: {{ worker.get_wwcc_status_display }}
</td>
```

3. Change the empty-state cell from seven columns to six:

```html
<td colspan="6">
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test workers.tests.SupportWorkerManagementTests.test_worker_list_omits_compliance_summary_but_detail_retains_it
```

Expected: `OK`, with one test passing.

- [ ] **Step 5: Run Worker regression tests and Django checks**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test workers.tests
.\.venv\Scripts\python.exe manage.py check
git diff --check
```

Expected: the Worker test suite passes, Django reports no issues, and `git diff --check` prints no errors.

- [ ] **Step 6: Review the rendered contract and commit the implementation**

Confirm the diff only changes the focused test and worker list template, then run:

```powershell
git add -- workers/tests.py templates/workers/worker_list.html
git commit -m "style: simplify support worker list"
```

Expected: one implementation commit on `codex/phase-113-worker-list-simplification`; the previously committed design document remains unchanged.
