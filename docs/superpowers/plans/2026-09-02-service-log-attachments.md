# Service Log Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make worker service log attachment submission all-or-nothing when private storage fails.

**Architecture:** Keep attachments as `Document` records linked to `ServiceLog`. Wrap service log creation, attachment document creation, and shift completion in one database transaction; if storage raises `StorageOperationError`, remove any files already stored during the request and return the worker to the form with a clear error.

**Tech Stack:** Django views, Django transactions, existing `Document` model and storage abstraction, Django test client.

---

### Task 1: Add Rollback Coverage

**Files:**
- Modify: `service_logs/tests_service_logs.py`
- Modify: `service_logs/views.py`

- [ ] **Step 1: Write the failing test**

Add a worker submission test that patches `Document.save` so the second attachment raises `StorageOperationError`. Assert the response renders the form with the private storage error, no `ServiceLog` remains, no `Document` remains, and the shift is not completed.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test service_logs.tests_service_logs.ServiceLogCompletionTests.test_attachment_storage_failure_rolls_back_service_log_submission
```

Expected before implementation: failure because the service log is created before the attachment storage exception escapes.

- [ ] **Step 3: Implement the minimal fix**

Wrap `worker_service_log_create` persistence in `transaction.atomic()`, catch `StorageOperationError`, delete any stored files collected during the request, add the error to the form, and render the existing form.

- [ ] **Step 4: Run focused and related tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test service_logs.tests_service_logs documents bscare_ndis.tests_settings
```

- [ ] **Step 5: Commit**

Commit only the spec, plan, tests, and implementation files for this phase.
