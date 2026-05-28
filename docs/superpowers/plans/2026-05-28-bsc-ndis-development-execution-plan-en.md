# Brisbane Star Care NDIS Online Admin System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the planning document into an executable roadmap and define the first buildable Phase 0 task list.

**Architecture:** Use a Django-first monolithic application with Django Templates for server-rendered pages and HTMX/Alpine.js only for lightweight interactions. Build the operational chain first: Participant -> Worker -> Assignment -> Shift -> Service Log -> Review -> Invoice, then add automation, integrations, and richer UI later.

**Tech Stack:** Django, Django Templates, local SQLite, production-ready PostgreSQL, HTMX, Alpine.js, Tailwind CSS or clean CSS.

---

## 1. Executive Decision

The first version should not start with a beautiful dashboard, drag-and-drop calendar, Xero integration, PRODA automation, or a mobile app. The first valuable version is the operational chain:

```text
Create Participant
-> Create Worker
-> Assign Worker
-> Create Shift
-> Worker Confirm
-> Worker Complete Service Log
-> Admin Approve
-> Create Invoice
```

Once this chain is stable, the system can replace a large amount of spreadsheet work, messaging, paper records, and manual follow-up. Every later feature should support or strengthen this chain.

---

## 2. Scope Boundary

### v1 Must Include

- Login, logout, and role-based redirect.
- Four roles: Super Admin, Admin, Support Worker, Accountant.
- Participant management.
- Support Worker management.
- Participant-Worker assignment.
- Support item management.
- Basic scheduling and roster.
- Worker views own shifts and confirms shifts.
- Worker completes a shift into a service log.
- Admin reviews, approves, and rejects service logs.
- Invoice generation from approved service logs.
- PDF/CSV exports.
- File upload and basic document management.
- Basic audit log, security configuration, and deployment readiness.

### v1 Should Not Include Yet

- Complex drag-and-drop calendar.
- Automatic intelligent rostering.
- GPS check-in/check-out.
- Native mobile app.
- Complex payroll or award calculations.
- Xero API automation.
- PRODA automated claiming.
- Participant or family portal.
- Complex NDIS budget forecast engine.
- SMS or push notification automation.

---

## 3. Planning Corrections

- [ ] **Correction 1: Clarify when the scheduling app is created**

The current document mentions creating the scheduling app in both Phase 0 and Phase 6. Recommendation: Phase 0 creates only the app skeleton; Phase 6 implements the Shift model, forms, views, templates, and business logic.

- [ ] **Correction 2: Disable manual service logs by default**

`/sw/logs/new/` should be configurable. In v1, disable unrostered manual logs by default. Only Super Admin should be able to enable them later from settings.

- [ ] **Correction 3: Lock service logs after invoicing**

Once a ServiceLog reaches `invoiced`, normal admins should not directly edit core fields. Corrections should go through an audit trail, void/reissue invoice flow, or credit note process.

- [ ] **Correction 4: Preserve historical support item pricing**

InvoiceLine must store the item number, description, unit price, quantity, GST, and line total as they were at invoice generation time. Do not rely only on the current SupportItem price.

- [ ] **Correction 5: Define whether draft shifts count for conflict checks**

Recommendation: in v1, `draft` shifts should count in worker conflict checks because drafts are often used for internal pre-scheduling. If the business wants drafts to be non-blocking, add a setting later.

---

## 4. Recommended Project Structure

Phase 0 should create this structure:

```text
bscare_ndis/
  manage.py
  requirements.txt
  README.md
  .env.example
  bscare_ndis/
    __init__.py
    settings.py
    urls.py
    wsgi.py
    asgi.py
  accounts/
    models.py
    views.py
    urls.py
    admin.py
    decorators.py
  core/
    views.py
    urls.py
  participants/
  workers/
  scheduling/
  service_logs/
  invoices/
  documents/
  templates/
    base.html
    admin_base.html
    worker_base.html
    accounts/login.html
    core/admin_dashboard.html
    core/worker_dashboard.html
    invoices/invoice_placeholder.html
  static/
    css/app.css
  media/
```

---

## 5. Development Roadmap

### Phase 0: Project Setup

**Goal:** Create the Django foundation, login/logout, role redirects, and placeholder dashboards.

**Acceptance Criteria:**
- The project runs locally.
- Django Admin is accessible.
- UserProfile supports four roles.
- Users redirect by role after login.
- Unauthenticated users are redirected to login.
- Worker cannot access the admin dashboard.
- Admin cannot access the worker dashboard.

### Phase 1: User Role and Permission

**Goal:** Establish permission decorators, role checks, and common access rules.

**Acceptance Criteria:**
- Support Worker can only access `/sw/*`.
- Admin and Super Admin can access admin operation pages.
- Accountant can only access invoice/export-related pages.
- Every page has an explicit permission check.

### Phase 2: Participant Management

**Goal:** Participant CRUD, list, filters, and detail page.

**Acceptance Criteria:**
- Admin can create, edit, search, and archive participants.
- Worker cannot see NDIS number, plan manager, funding, or internal notes.
- Participant detail includes roster/logs/invoices/documents/assigned workers tabs.

### Phase 3: Support Worker Management

**Goal:** Worker profile, login account, and compliance information.

**Acceptance Criteria:**
- Creating a worker also creates a Django User.
- Worker can log in.
- Worker profile and UserProfile are linked correctly.
- Expired compliance documents show warnings.

### Phase 4: Assignment

**Goal:** Bind participants and workers.

**Acceptance Criteria:**
- The same participant + worker cannot have duplicate active assignments.
- Ending an assignment does not delete historical shifts, logs, or invoices.
- Worker access and submission options are based on assigned participants.

### Phase 5: Support Item Management

**Goal:** Manage NDIS support items.

**Acceptance Criteria:**
- Admin can maintain item number, name, category, unit, price, and GST code.
- Only active support items appear in shift/log/invoice forms.
- The system does not invent real NDIS item numbers.

### Phase 6: Basic Scheduling

**Goal:** Implement Shift model, roster list, create/edit/detail pages, worker my shifts, and shift confirmation.

**Acceptance Criteria:**
- Admin can create a draft shift.
- Admin can publish a shift.
- Worker can only see their own published/confirmed shifts.
- Worker can confirm a published shift.
- Worker overlapping active shifts are blocked.
- Shift list filters work.

### Phase 7: Complete Shift to Service Log

**Goal:** Allow a worker to complete a shift and submit a service log.

**Acceptance Criteria:**
- Worker can only complete their own shift.
- One shift can create only one service log.
- ServiceLog is created with status `submitted`.
- Shift changes to `completed` and stores `completed_at`.
- Admin can see the relationship between shift and service log.

### Phase 8: Admin Service Log Review

**Goal:** Admin reviews service logs.

**Acceptance Criteria:**
- Submitted logs can be approved or rejected.
- Reject requires a reason.
- Worker can see rejection reason.
- Only approved logs can move into invoicing.

### Phase 9: Invoice Generation

**Goal:** Create invoices from approved not-invoiced service logs.

**Acceptance Criteria:**
- Create invoice page loads logs by participant and period.
- Only approved and not-invoiced logs are loaded.
- InvoiceLine stores historical unit price and description.
- Related logs become `invoiced` after invoice creation.

### Phase 10: Invoice PDF/CSV Export

**Goal:** Generate invoice PDF/CSV and track sent/paid/cancelled statuses.

**Acceptance Criteria:**
- Invoice detail can download PDF.
- Invoice list/export can download CSV.
- Payment status can be updated.
- Invoiced logs cannot have core fields edited directly.

### Phase 11: Recurring Shifts

**Goal:** Simple weekly/fortnightly repeated shifts.

**Acceptance Criteria:**
- Preview is required before creation.
- Worker conflicts are skipped.
- Result page shows created count and skipped count.

### Phase 12: Documents and Hardening

**Goal:** File upload, mobile polish, security, audit, and production configuration.

**Acceptance Criteria:**
- Files can link to participant/worker/invoice/service log.
- File permissions follow role and object permissions.
- Secrets are managed through `.env`.
- PostgreSQL production readiness is clear.
- Media backup strategy is defined.
- AuditLog covers approve/reject/cancel/invoice/delete operations.

---

## 6. Phase 0 Detailed Task List

### Task 0.1: Create Project Environment

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: Create requirements.txt**

```text
Django>=5.0,<6.0
python-dotenv>=1.0,<2.0
Pillow>=10.0,<12.0
```

- [ ] **Step 2: Create the Django project**

Run:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
django-admin startproject bscare_ndis .
```

Expected:

```text
manage.py exists
bscare_ndis/settings.py exists
```

- [ ] **Step 3: Create apps**

Run:

```bash
python manage.py startapp accounts
python manage.py startapp core
python manage.py startapp participants
python manage.py startapp workers
python manage.py startapp scheduling
python manage.py startapp service_logs
python manage.py startapp invoices
python manage.py startapp documents
```

Expected: Each app folder exists and contains `models.py`, `views.py`, `admin.py`, and `apps.py`.

### Task 0.2: Configure Settings

**Files:**
- Modify: `bscare_ndis/settings.py`
- Create: `templates/`
- Create: `static/css/app.css`
- Create: `media/`

- [ ] **Step 1: Add apps**

Add these to `INSTALLED_APPS`:

```python
"accounts",
"core",
"participants",
"workers",
"scheduling",
"service_logs",
"invoices",
"documents",
```

- [ ] **Step 2: Configure templates/static/media**

Ensure `DIRS` points to `BASE_DIR / "templates"` and add:

```python
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "role_redirect"
LOGOUT_REDIRECT_URL = "login"
```

### Task 0.3: UserProfile and Roles

**Files:**
- Modify: `accounts/models.py`
- Modify: `accounts/admin.py`

- [ ] **Step 1: Create UserProfile model**

```python
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        SUPPORT_WORKER = "support_worker", "Support Worker"
        ACCOUNTANT = "accountant", "Accountant"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=Role.choices)
    phone = models.CharField(max_length=30, blank=True)
    is_active_worker = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
```

- [ ] **Step 2: Register admin**

```python
from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "is_active_worker", "created_at")
    list_filter = ("role", "is_active_worker")
    search_fields = ("user__username", "user__email", "phone")
```

- [ ] **Step 3: Run migrations**

Run:

```bash
python manage.py makemigrations
python manage.py migrate
```

Expected: Migrations complete successfully with no errors.

### Task 0.4: Login, Logout, and Role Redirect

**Files:**
- Create: `accounts/views.py`
- Create: `accounts/urls.py`
- Modify: `bscare_ndis/urls.py`
- Create: `templates/accounts/login.html`

- [ ] **Step 1: Create role_redirect view**

```python
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


class BSCLoginView(LoginView):
    template_name = "accounts/login.html"


class BSCLogoutView(LogoutView):
    pass


@login_required
def role_redirect(request):
    profile = getattr(request.user, "userprofile", None)
    if profile is None:
        return redirect("login")
    if profile.role in ["super_admin", "admin"]:
        return redirect("admin_dashboard")
    if profile.role == "support_worker":
        return redirect("worker_dashboard")
    if profile.role == "accountant":
        return redirect("invoice_placeholder")
    return redirect("login")
```

- [ ] **Step 2: Create accounts urls**

```python
from django.urls import path
from .views import BSCLoginView, BSCLogoutView, role_redirect

urlpatterns = [
    path("login/", BSCLoginView.as_view(), name="login"),
    path("logout/", BSCLogoutView.as_view(), name="logout"),
    path("role-redirect/", role_redirect, name="role_redirect"),
]
```

### Task 0.5: Base Pages and Permissions

**Files:**
- Create: `accounts/decorators.py`
- Create: `core/views.py`
- Create: `core/urls.py`
- Create: `invoices/views.py`
- Create: `invoices/urls.py`
- Create: `templates/base.html`
- Create: `templates/admin_base.html`
- Create: `templates/worker_base.html`
- Create: `templates/core/admin_dashboard.html`
- Create: `templates/core/worker_dashboard.html`
- Create: `templates/invoices/invoice_placeholder.html`

- [ ] **Step 1: Create role decorator**

```python
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            profile = getattr(request.user, "userprofile", None)
            if profile is None or profile.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

- [ ] **Step 2: Create placeholder views**

```python
from django.shortcuts import render
from accounts.decorators import role_required


@role_required("super_admin", "admin")
def admin_dashboard(request):
    return render(request, "core/admin_dashboard.html")


@role_required("support_worker")
def worker_dashboard(request):
    return render(request, "core/worker_dashboard.html")
```

Invoice placeholder:

```python
from django.shortcuts import render
from accounts.decorators import role_required


@role_required("super_admin", "admin", "accountant")
def invoice_placeholder(request):
    return render(request, "invoices/invoice_placeholder.html")
```

### Task 0.6: Phase 0 Acceptance Testing

- [ ] **Step 1: Create superuser**

Run:

```bash
python manage.py createsuperuser
```

- [ ] **Step 2: Create UserProfile for superuser**

In Django Admin, create:

```text
user = created superuser
role = super_admin
```

- [ ] **Step 3: Manual tests**

Run:

```bash
python manage.py runserver
```

Manual checks:

```text
Open http://127.0.0.1:8000/login/
Login as super_admin -> redirects to /admin-dashboard/
Open /sw/dashboard/ as super_admin -> PermissionDenied
Create support_worker user and profile
Login as support_worker -> redirects to /sw/dashboard/
Open /admin-dashboard/ as support_worker -> PermissionDenied
Create accountant user and profile
Login as accountant -> redirects to /invoices/
```

---

## 7. Security, Privacy, and Audit Checklist

- [ ] Worker querysets must always filter by the current worker profile.
- [ ] Worker pages must not expose participant NDIS number, funding, plan manager, invoice data, or internal notes.
- [ ] All approve/reject/cancel/invoice/delete actions must write AuditLog records.
- [ ] File uploads must restrict file type and file size.
- [ ] File access must check object permission; users must not download files by guessing URLs.
- [ ] `.env` must store secret key, database URL, and allowed hosts.
- [ ] `DEBUG` must be disabled in production.
- [ ] Database and media files must have a backup strategy.
- [ ] Invoiced logs must not be edited directly by normal admins.
- [ ] Exported fields must be restricted by role.

---

## 8. Recommended Execution Mode

Plan complete and saved to `docs/superpowers/plans/2026-05-28-bsc-ndis-development-execution-plan-en.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh agent per phase, with review and integration in the main session.

**2. Inline Execution** - Execute phases in this session with checkpoints after each phase.

Recommended next step: start with **Phase 0 Inline Execution**, because the project does not yet have a codebase and the foundation should be made runnable first.
