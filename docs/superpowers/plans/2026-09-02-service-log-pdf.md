# Service Log PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin-only service log PDF download.

**Architecture:** Reuse the existing invoice PDF helper functions and static logo asset to generate a one-page PDF on demand from `ServiceLog`. Add one admin-protected route and one button on the admin service log detail screen.

**Tech Stack:** Django views and URL routing, existing lightweight PDF helpers in `invoices.views`, existing `static/img/bsc-logo.png`, Django test client.

---

### Task 1: Define Admin PDF Behavior

**Files:**
- Modify: `service_logs/tests_review.py`
- Modify: `service_logs/urls.py`
- Modify: `service_logs/views.py`
- Modify: `templates/service_logs/service_log_detail.html`

- [ ] **Step 1: Write failing tests**

Add tests for `service_log_pdf`: admin gets `application/pdf`, content starts with `%PDF`, the PDF stream includes service log data and attachment filenames, the filename follows `ServiceLog_<date>_<id>_<participant>.pdf`, the detail page links to the route, and worker access redirects away from the admin-only endpoint.

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test service_logs.tests_review.ServiceLogReviewTests.test_admin_can_download_service_log_pdf service_logs.tests_review.ServiceLogReviewTests.test_service_log_pdf_uses_clear_download_filename service_logs.tests_review.ServiceLogReviewTests.test_admin_service_log_detail_links_to_pdf service_logs.tests_review.ServiceLogReviewTests.test_worker_cannot_download_admin_service_log_pdf
```

Expected before implementation: URL reverse failures because `service_log_pdf` does not exist.

- [ ] **Step 3: Implement minimal route, view, and button**

Add `service_log_pdf` to `service_logs.views`, register `service-logs/<int:service_log_id>/pdf/`, and place `Download PDF` in the admin detail header.

- [ ] **Step 4: Run focused and related tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test service_logs.tests_review service_logs.tests_service_logs invoices.tests_exports
.\.venv\Scripts\python.exe manage.py check
```

- [ ] **Step 5: Commit**

Commit only the service log PDF spec, plan, tests, view, URL, and template changes.
