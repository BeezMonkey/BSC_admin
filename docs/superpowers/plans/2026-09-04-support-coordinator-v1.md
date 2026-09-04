# Support Coordinator V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate Support Coordinator portal and admin-managed Coordination Log workflow without changing support worker, roster, service log, document, or invoice behavior.

**Architecture:** Add a new `coordinators` Django app for SC profiles, participant assignments, SC portal views, and coordination-log review. Extend `accounts.UserProfile.Role` with a dedicated `support_coordinator` role and route SC users to their own portal. Keep `CoordinationLog` separate from worker `ServiceLog` so invoices remain untouched in V1.

**Tech Stack:** Django 5.2, Django templates, existing `app.css`, Django TestCase, SQLite/Postgres-compatible migrations.

---

## File Structure

- Create `coordinators/` app: models, forms, views, urls, admin, apps, migrations, tests.
- Modify `bscare_ndis/settings.py`: add `coordinators` to `INSTALLED_APPS`.
- Modify `bscare_ndis/urls.py`: include coordinator routes.
- Modify `accounts/models.py`: add `SUPPORT_COORDINATOR` role choice.
- Modify `accounts/permissions.py`: expose coordinator role tuple.
- Modify `accounts/decorators.py`: expose `coordinator_required`.
- Modify `accounts/views.py`: redirect SC users to SC dashboard and add SC login portal copy if needed.
- Modify `core/models.py`: add audit actions for coordinator management and coordination-log review.
- Modify `templates/admin_base.html`: add Admin sidebar entries for `Support Coordinators` and `Coordination Logs`.
- Create `templates/coordinators/`: admin and SC portal templates.
- Modify `static/css/app.css`: add small, reusable SC portal/admin styles only where existing classes are insufficient.

---

### Task 1: Role, App, And Route Foundation

**Files:**
- Create: `coordinators/__init__.py`
- Create: `coordinators/apps.py`
- Create: `coordinators/urls.py`
- Create: `coordinators/views.py`
- Create: `coordinators/tests.py`
- Create: `templates/coordinators/sc_dashboard.html`
- Create: `templates/coordinator_base.html`
- Modify: `bscare_ndis/settings.py`
- Modify: `bscare_ndis/urls.py`
- Modify: `accounts/models.py`
- Modify: `accounts/permissions.py`
- Modify: `accounts/decorators.py`
- Modify: `accounts/views.py`

- [ ] **Step 1: Write failing role and access tests**

Add these tests to `coordinators/tests.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile


class CoordinatorRoleAccessTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="pass12345",
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def test_role_redirect_sends_support_coordinator_to_sc_dashboard(self):
        user = self.create_user_with_role(
            "coordinator",
            UserProfile.Role.SUPPORT_COORDINATOR,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("role_redirect"))

        self.assertRedirects(response, reverse("coordinator_dashboard"))

    def test_support_coordinator_can_access_sc_dashboard(self):
        user = self.create_user_with_role(
            "coordinator",
            UserProfile.Role.SUPPORT_COORDINATOR,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("coordinator_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Support Coordinator")

    def test_support_worker_cannot_access_sc_dashboard(self):
        user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("coordinator_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_support_coordinator_cannot_access_admin_dashboard(self):
        user = self.create_user_with_role(
            "coordinator",
            UserProfile.Role.SUPPORT_COORDINATOR,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorRoleAccessTests
```

Expected: FAIL because `coordinators` app, `SUPPORT_COORDINATOR`, and `coordinator_dashboard` do not exist.

- [ ] **Step 3: Add minimal app, role, decorator, redirect, and dashboard**

Create `coordinators/apps.py`:

```python
from django.apps import AppConfig


class CoordinatorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "coordinators"
```

Create `coordinators/views.py`:

```python
from django.shortcuts import render

from accounts.decorators import coordinator_required


@coordinator_required
def coordinator_dashboard(request):
    return render(request, "coordinators/sc_dashboard.html")
```

Create `coordinators/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("sc/dashboard/", views.coordinator_dashboard, name="coordinator_dashboard"),
]
```

Create `templates/coordinator_base.html`:

```django
{% extends "base.html" %}

{% block body %}
<div class="app-shell worker-app-shell">
  <aside class="sidebar worker-sidebar">
    <div class="brand">
      <span>Brisbane Star Care</span>
      <small>Support Coordinator</small>
    </div>
    <nav class="sidebar-nav worker-sidebar-nav" aria-label="Support coordinator navigation">
      <a class="sidebar-link{% if request.resolver_match.url_name == 'coordinator_dashboard' %} active{% endif %}" href="{% url 'coordinator_dashboard' %}">Dashboard</a>
    </nav>
  </aside>
  <section class="content worker-main">
    <header class="topbar worker-topbar">
      <span class="user-label">{{ request.user.get_username }}</span>
      <form method="post" action="{% url 'logout' %}">
        {% csrf_token %}
        <button class="button secondary topbar-logout" type="submit">Logout</button>
      </form>
    </header>
    {% if messages %}
      <div class="messages" role="status" aria-live="polite">
        {% for message in messages %}
          <div class="message {{ message.tags }}">{{ message }}</div>
        {% endfor %}
      </div>
    {% endif %}
    {% block content %}{% endblock %}
  </section>
</div>
{% endblock %}
```

Create `templates/coordinators/sc_dashboard.html`:

```django
{% extends "coordinator_base.html" %}

{% block content %}
<div class="page-header">
  <div>
    <h1>Support Coordinator Dashboard</h1>
    <p>Manage your assigned participants and coordination logs.</p>
  </div>
</div>
{% endblock %}
```

Modify `accounts/models.py` role choices:

```python
class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Admin"
    SUPPORT_WORKER = "support_worker", "Support Worker"
    SUPPORT_COORDINATOR = "support_coordinator", "Support Coordinator"
    ACCOUNTANT = "accountant", "Accountant"
```

Modify `accounts/permissions.py`:

```python
SUPPORT_COORDINATOR = UserProfile.Role.SUPPORT_COORDINATOR
COORDINATOR_ROLES = (SUPPORT_COORDINATOR,)
```

Keep existing constants and tuples.

Modify `accounts/decorators.py` imports and aliases:

```python
from .permissions import ADMIN_ROLES, COORDINATOR_ROLES, FINANCE_ROLES, WORKER_ROLES, has_role

coordinator_required = role_required(*COORDINATOR_ROLES)
```

Modify `accounts/views.py` imports and redirect:

```python
from .permissions import ACCOUNTANT, ADMIN_ROLES, SUPPORT_COORDINATOR, SUPPORT_WORKER, get_role

if role == SUPPORT_COORDINATOR:
    return redirect("coordinator_dashboard")
```

Modify `bscare_ndis/settings.py`:

```python
"coordinators",
```

Modify `bscare_ndis/urls.py`:

```python
path("", include("coordinators.urls")),
```

- [ ] **Step 4: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorRoleAccessTests accounts.tests
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add accounts bscare_ndis coordinators templates/coordinator_base.html templates/coordinators/sc_dashboard.html
git commit -m "Add support coordinator role and portal shell"
```

---

### Task 2: Coordinator Data Models

**Files:**
- Create: `coordinators/models.py`
- Create: `coordinators/admin.py`
- Modify: `coordinators/tests.py`
- Create: `coordinators/migrations/0001_initial.py`

- [ ] **Step 1: Write failing model tests**

Append to `coordinators/tests.py`:

```python
from datetime import date, time
from decimal import Decimal

from participants.models import Participant

from .models import CoordinationLog, ParticipantCoordinatorAssignment, SupportCoordinator


def create_coordinator(username="coord"):
    user = get_user_model().objects.create_user(
        username=username,
        password="pass12345",
    )
    UserProfile.objects.create(
        user=user,
        role=UserProfile.Role.SUPPORT_COORDINATOR,
    )
    return SupportCoordinator.objects.create(
        user=user,
        first_name="Casey",
        last_name="Coordinator",
        email=f"{username}@example.com",
    )


def create_participant(first_name="Demo", last_name="Participant"):
    return Participant.objects.create(
        first_name=first_name,
        last_name=last_name,
        status=Participant.Status.ACTIVE,
    )


class CoordinatorModelTests(TestCase):

    def test_support_coordinator_display_name(self):
        coordinator = create_coordinator()

        self.assertEqual(coordinator.display_name, "Casey Coordinator")
        self.assertEqual(str(coordinator), "Casey Coordinator")

    def test_assignment_tracks_active_participant_access(self):
        coordinator = create_coordinator()
        participant = create_participant()

        assignment = ParticipantCoordinatorAssignment.objects.create(
            participant=participant,
            coordinator=coordinator,
            start_date=date(2026, 9, 4),
        )

        self.assertTrue(assignment.is_active)
        self.assertEqual(str(assignment), "Demo Participant -> Casey Coordinator")

    def test_coordination_log_defaults_to_submitted(self):
        coordinator = create_coordinator()
        participant = create_participant()

        log = CoordinationLog.objects.create(
            participant=participant,
            coordinator=coordinator,
            service_date=date(2026, 9, 4),
            start_time=time(9, 0),
            end_time=time(10, 30),
            break_minutes=0,
            actual_hours=Decimal("1.50"),
            coordination_type=CoordinationLog.CoordinationType.GENERAL,
            case_notes="Called provider and updated participant record.",
        )

        self.assertEqual(log.status, CoordinationLog.Status.SUBMITTED)
        self.assertEqual(str(log), "2026-09-04 Demo Participant / Casey Coordinator")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorModelTests
```

Expected: FAIL because the model classes do not exist.

- [ ] **Step 3: Add models**

Create `coordinators/models.py`:

```python
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class SupportCoordinator(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        parts = [self.first_name, self.last_name]
        letters = [part.strip()[0] for part in parts if part and part.strip()]
        return "".join(letters[:2]).upper() or "C"

    def get_absolute_url(self):
        return reverse("coordinator_detail", args=[self.id])


class ParticipantCoordinatorAssignment(models.Model):
    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.CASCADE,
        related_name="coordinator_assignments",
    )
    coordinator = models.ForeignKey(
        SupportCoordinator,
        on_delete=models.CASCADE,
        related_name="participant_assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-start_date", "coordinator__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "coordinator"],
                condition=models.Q(is_active=True),
                name="unique_active_participant_coordinator_assignment",
            )
        ]

    def __str__(self):
        return f"{self.participant} -> {self.coordinator}"


class CoordinationLog(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class CoordinationType(models.TextChoices):
        GENERAL = "general", "General coordination"
        PARTICIPANT_CONTACT = "participant_contact", "Participant / family contact"
        PROVIDER_CONTACT = "provider_contact", "Provider contact"
        PLAN_REVIEW = "plan_review", "Plan review / funding discussion"
        INCIDENT_FOLLOW_UP = "incident_follow_up", "Incident or concern follow-up"
        OTHER = "other", "Other"

    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.PROTECT,
        related_name="coordination_logs",
    )
    coordinator = models.ForeignKey(
        SupportCoordinator,
        on_delete=models.PROTECT,
        related_name="coordination_logs",
    )
    service_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=0)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2)
    coordination_type = models.CharField(
        max_length=40,
        choices=CoordinationType.choices,
        default=CoordinationType.GENERAL,
    )
    case_notes = models.TextField()
    coordinator_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_coordination_logs",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-service_date", "-submitted_at"]

    def __str__(self):
        return f"{self.service_date} {self.participant} / {self.coordinator}"

    def get_absolute_url(self):
        return reverse("coordination_log_detail", args=[self.id])
```

Create `coordinators/admin.py`:

```python
from django.contrib import admin

from .models import CoordinationLog, ParticipantCoordinatorAssignment, SupportCoordinator


@admin.register(SupportCoordinator)
class SupportCoordinatorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "email", "phone", "status")
    list_filter = ("status",)
    search_fields = ("first_name", "last_name", "email", "phone")


@admin.register(ParticipantCoordinatorAssignment)
class ParticipantCoordinatorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("participant", "coordinator", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = (
        "participant__first_name",
        "participant__last_name",
        "coordinator__first_name",
        "coordinator__last_name",
    )


@admin.register(CoordinationLog)
class CoordinationLogAdmin(admin.ModelAdmin):
    list_display = ("service_date", "participant", "coordinator", "coordination_type", "actual_hours", "status")
    list_filter = ("status", "coordination_type")
    search_fields = (
        "participant__first_name",
        "participant__last_name",
        "coordinator__first_name",
        "coordinator__last_name",
        "case_notes",
    )
```

- [ ] **Step 4: Create migration**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations coordinators
```

Expected: creates `coordinators/migrations/0001_initial.py`.

- [ ] **Step 5: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorModelTests
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add coordinators
git commit -m "Add support coordinator data models"
```

---

### Task 3: Admin Support Coordinator Management

**Files:**
- Create: `coordinators/forms.py`
- Modify: `coordinators/views.py`
- Modify: `coordinators/urls.py`
- Modify: `coordinators/tests.py`
- Create: `templates/coordinators/coordinator_list.html`
- Create: `templates/coordinators/coordinator_form.html`
- Create: `templates/coordinators/coordinator_detail.html`
- Create: `templates/coordinators/coordinator_assignment_form.html`
- Modify: `templates/admin_base.html`

- [ ] **Step 1: Write failing admin management tests**

Append to `coordinators/tests.py`:

```python
class CoordinatorAdminManagementTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="admin",
            password="pass12345",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN,
        )
        self.client.force_login(self.admin_user)

    def test_admin_can_create_support_coordinator(self):
        response = self.client.post(
            reverse("coordinator_create"),
            {
                "username": "casey",
                "password1": "CoordinatorPass123!",
                "password2": "CoordinatorPass123!",
                "account_active": "on",
                "first_name": "Casey",
                "last_name": "Coordinator",
                "email": "casey@example.com",
                "phone": "0400000000",
                "status": SupportCoordinator.Status.ACTIVE,
                "notes": "Trial coordinator",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        coordinator = SupportCoordinator.objects.get(email="casey@example.com")
        self.assertEqual(coordinator.user.userprofile.role, UserProfile.Role.SUPPORT_COORDINATOR)
        self.assertTrue(coordinator.user.check_password("CoordinatorPass123!"))
        self.assertTrue(coordinator.user.is_active)
        self.assertContains(response, "Support coordinator created.")

    def test_admin_can_assign_participant_to_coordinator(self):
        coordinator = create_coordinator("coord-for-assignment")
        participant = Participant.objects.create(
            first_name="Demo",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )

        response = self.client.post(
            reverse("coordinator_assign_participant", args=[coordinator.id]),
            {
                "participant": participant.id,
                "start_date": "2026-09-04",
                "end_date": "",
                "is_active": "on",
                "notes": "SC support",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ParticipantCoordinatorAssignment.objects.filter(
                participant=participant,
                coordinator=coordinator,
                is_active=True,
            ).exists()
        )
        self.assertContains(response, "Participant assigned to support coordinator.")

    def test_admin_can_update_support_coordinator(self):
        coordinator = create_coordinator("coord-for-edit")

        response = self.client.post(
            reverse("coordinator_edit", args=[coordinator.id]),
            {
                "email": "updated-coordinator@example.com",
                "first_name": "Updated",
                "last_name": "Coordinator",
                "phone": "0411111111",
                "status": SupportCoordinator.Status.INACTIVE,
                "notes": "Paused access",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        coordinator.refresh_from_db()
        self.assertEqual(coordinator.email, "updated-coordinator@example.com")
        self.assertEqual(coordinator.status, SupportCoordinator.Status.INACTIVE)
        self.assertFalse(coordinator.user.is_active)
        self.assertContains(response, "Support coordinator updated.")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorAdminManagementTests
```

Expected: FAIL because admin forms and routes do not exist.

- [ ] **Step 3: Add admin forms**

Create `coordinators/forms.py`:

```python
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import UserProfile
from participants.models import Participant

from .models import ParticipantCoordinatorAssignment, SupportCoordinator


class SupportCoordinatorCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)
    account_active = forms.BooleanField(label="Login enabled", required=False, initial=True)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=30, required=False)
    status = forms.ChoiceField(choices=SupportCoordinator.Status.choices)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if get_user_model().objects.filter(email=email).exists() or SupportCoordinator.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = get_user_model().objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password1"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_active=data["account_active"],
        )
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPPORT_COORDINATOR,
            phone=data["phone"],
        )
        return SupportCoordinator.objects.create(
            user=user,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            status=data["status"],
            notes=data["notes"],
        )


class SupportCoordinatorEditForm(forms.ModelForm):
    account_active = forms.BooleanField(label="Login enabled", required=False)

    class Meta:
        model = SupportCoordinator
        fields = ["email", "first_name", "last_name", "phone", "status", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["account_active"].initial = self.instance.user.is_active

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        duplicate_user = get_user_model().objects.filter(email=email).exclude(
            pk=self.instance.user_id
        )
        duplicate_coordinator = SupportCoordinator.objects.filter(email=email).exclude(
            pk=self.instance.pk
        )
        if duplicate_user.exists() or duplicate_coordinator.exists():
            raise forms.ValidationError("Email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        coordinator = super().save(commit=False)
        coordinator.user.email = self.cleaned_data["email"]
        coordinator.user.first_name = self.cleaned_data["first_name"]
        coordinator.user.last_name = self.cleaned_data["last_name"]
        coordinator.user.is_active = self.cleaned_data["account_active"]
        if commit:
            coordinator.user.save()
            coordinator.save()
            profile, _ = UserProfile.objects.get_or_create(
                user=coordinator.user,
                defaults={"role": UserProfile.Role.SUPPORT_COORDINATOR},
            )
            profile.role = UserProfile.Role.SUPPORT_COORDINATOR
            profile.phone = coordinator.phone
            profile.save()
        return coordinator


class ParticipantCoordinatorAssignmentForm(forms.ModelForm):
    participant = forms.ModelChoiceField(
        queryset=Participant.objects.filter(status=Participant.Status.ACTIVE),
    )

    class Meta:
        model = ParticipantCoordinatorAssignment
        fields = ["participant", "start_date", "end_date", "is_active", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
```

- [ ] **Step 4: Add admin views and routes**

Extend `coordinators/views.py`:

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required, coordinator_required

from .forms import (
    ParticipantCoordinatorAssignmentForm,
    SupportCoordinatorCreateForm,
    SupportCoordinatorEditForm,
)
from .models import ParticipantCoordinatorAssignment, SupportCoordinator


@admin_required
def coordinator_list(request):
    coordinators = SupportCoordinator.objects.all()
    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    if status:
        coordinators = coordinators.filter(status=status)
    if query:
        coordinators = coordinators.filter(
            models.Q(first_name__icontains=query)
            | models.Q(last_name__icontains=query)
            | models.Q(email__icontains=query)
            | models.Q(phone__icontains=query)
        )
    return render(
        request,
        "coordinators/coordinator_list.html",
        {
            "coordinators": coordinators,
            "status_choices": SupportCoordinator.Status.choices,
            "status": status,
            "query": query,
        },
    )


@admin_required
def coordinator_detail(request, coordinator_id):
    coordinator = get_object_or_404(SupportCoordinator, id=coordinator_id)
    assignments = coordinator.participant_assignments.select_related("participant")
    return render(
        request,
        "coordinators/coordinator_detail.html",
        {"coordinator": coordinator, "assignments": assignments},
    )


@admin_required
def coordinator_create(request):
    if request.method == "POST":
        form = SupportCoordinatorCreateForm(request.POST)
        if form.is_valid():
            coordinator = form.save()
            messages.success(request, "Support coordinator created.")
            return redirect("coordinator_detail", coordinator_id=coordinator.id)
    else:
        form = SupportCoordinatorCreateForm()
    return render(request, "coordinators/coordinator_form.html", {"form": form})


@admin_required
def coordinator_edit(request, coordinator_id):
    coordinator = get_object_or_404(SupportCoordinator.objects.select_related("user"), id=coordinator_id)
    if request.method == "POST":
        form = SupportCoordinatorEditForm(request.POST, instance=coordinator)
        if form.is_valid():
            coordinator = form.save()
            messages.success(request, "Support coordinator updated.")
            return redirect("coordinator_detail", coordinator_id=coordinator.id)
    else:
        form = SupportCoordinatorEditForm(instance=coordinator)
    return render(
        request,
        "coordinators/coordinator_form.html",
        {"form": form, "coordinator": coordinator},
    )


@admin_required
def coordinator_assign_participant(request, coordinator_id):
    coordinator = get_object_or_404(SupportCoordinator, id=coordinator_id)
    if request.method == "POST":
        form = ParticipantCoordinatorAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.coordinator = coordinator
            assignment.save()
            messages.success(request, "Participant assigned to support coordinator.")
            return redirect("coordinator_detail", coordinator_id=coordinator.id)
    else:
        form = ParticipantCoordinatorAssignmentForm()
    return render(
        request,
        "coordinators/coordinator_assignment_form.html",
        {"form": form, "coordinator": coordinator},
    )
```

Add `from django.db import models` at the top of `coordinators/views.py`.

Extend `coordinators/urls.py`:

```python
path("coordinators/", views.coordinator_list, name="coordinator_list"),
path("coordinators/new/", views.coordinator_create, name="coordinator_create"),
path("coordinators/<int:coordinator_id>/", views.coordinator_detail, name="coordinator_detail"),
path("coordinators/<int:coordinator_id>/edit/", views.coordinator_edit, name="coordinator_edit"),
path(
    "coordinators/<int:coordinator_id>/assign/",
    views.coordinator_assign_participant,
    name="coordinator_assign_participant",
),
```

- [ ] **Step 5: Add simple templates**

Use existing Admin table/card classes. Include fields from the forms and a primary submit button. Keep copy concise:

```django
{% extends "admin_base.html" %}

{% block content %}
<div class="page-header">
  <div>
    <h1>Support Coordinators</h1>
    <p>Manage support coordinator access and participant assignments.</p>
  </div>
  <a class="button" href="{% url 'coordinator_create' %}">New Coordinator</a>
</div>
{% endblock %}
```

Create detail and form templates with the same `page-header`, `card`, `detail-list`, and `button-row` patterns already used in workers and participants templates.

Update `templates/admin_base.html` Operations nav:

```django
<a class="sidebar-link{% if request.resolver_match.url_name == 'coordinator_list' or request.resolver_match.url_name == 'coordinator_create' or request.resolver_match.url_name == 'coordinator_detail' or request.resolver_match.url_name == 'coordinator_edit' or request.resolver_match.url_name == 'coordinator_assign_participant' %} active{% endif %}" href="{% url 'coordinator_list' %}">Support Coordinators</a>
```

- [ ] **Step 6: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorAdminManagementTests
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add coordinators templates/admin_base.html templates/coordinators
git commit -m "Add admin support coordinator management"
```

---

### Task 4: SC Participant Access And Dashboard

**Files:**
- Modify: `coordinators/views.py`
- Modify: `coordinators/urls.py`
- Modify: `coordinators/tests.py`
- Modify: `templates/coordinator_base.html`
- Modify: `templates/coordinators/sc_dashboard.html`
- Create: `coordinators/querysets.py`
- Create: `templates/coordinators/sc_participant_list.html`
- Create: `templates/coordinators/sc_participant_detail.html`

- [ ] **Step 1: Write failing SC participant visibility tests**

Append to `coordinators/tests.py`:

```python
class CoordinatorPortalParticipantTests(TestCase):
    def setUp(self):
        self.coordinator = create_coordinator("coord-portal")
        self.assigned = Participant.objects.create(
            first_name="Assigned",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
            worker_visible_notes="Use side entrance.",
            internal_notes="Admin only.",
        )
        self.unassigned = Participant.objects.create(
            first_name="Hidden",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.assigned,
            coordinator=self.coordinator,
            start_date=date(2026, 9, 4),
        )
        self.client.force_login(self.coordinator.user)

    def test_sc_participant_list_shows_only_assigned_participants(self):
        response = self.client.get(reverse("coordinator_participant_list"))

        self.assertContains(response, "Assigned Participant")
        self.assertNotContains(response, "Hidden Participant")

    def test_sc_participant_detail_hides_internal_notes(self):
        response = self.client.get(
            reverse("coordinator_participant_detail", args=[self.assigned.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use side entrance.")
        self.assertNotContains(response, "Admin only.")

    def test_sc_cannot_view_unassigned_participant_detail(self):
        response = self.client.get(
            reverse("coordinator_participant_detail", args=[self.unassigned.id])
        )

        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorPortalParticipantTests
```

Expected: FAIL because SC participant routes do not exist.

- [ ] **Step 3: Add SC queryset helper and views**

Create `coordinators/querysets.py`:

```python
from participants.models import Participant

from .models import SupportCoordinator


def assigned_participants_for(coordinator):
    if coordinator is None:
        return Participant.objects.none()
    return Participant.objects.filter(
        status=Participant.Status.ACTIVE,
        coordinator_assignments__coordinator=coordinator,
        coordinator_assignments__is_active=True,
        coordinator_assignments__coordinator__status=SupportCoordinator.Status.ACTIVE,
    ).distinct()
```

Add to `coordinators/views.py`:

```python
from participants.models import Participant

from .querysets import assigned_participants_for


def get_current_coordinator(user):
    return getattr(user, "supportcoordinator", None)


@coordinator_required
def coordinator_participant_list(request):
    coordinator = get_current_coordinator(request.user)
    participants = Participant.objects.none()
    if coordinator:
        participants = assigned_participants_for(coordinator)
    return render(
        request,
        "coordinators/sc_participant_list.html",
        {"participants": participants},
    )


@coordinator_required
def coordinator_participant_detail(request, participant_id):
    coordinator = get_current_coordinator(request.user)
    participant = get_object_or_404(
        assigned_participants_for(coordinator),
        id=participant_id,
    )
    return render(
        request,
        "coordinators/sc_participant_detail.html",
        {"participant": participant},
    )
```

Update dashboard to pass counts:

```python
@coordinator_required
def coordinator_dashboard(request):
    coordinator = get_current_coordinator(request.user)
    assigned_count = 0
    if coordinator:
        assigned_count = assigned_participants_for(coordinator).count()
    return render(
        request,
        "coordinators/sc_dashboard.html",
        {"assigned_participant_count": assigned_count},
    )
```

Extend `coordinators/urls.py`:

```python
path("sc/participants/", views.coordinator_participant_list, name="coordinator_participant_list"),
path(
    "sc/participants/<int:participant_id>/",
    views.coordinator_participant_detail,
    name="coordinator_participant_detail",
),
```

- [ ] **Step 4: Add templates and nav**

Update `templates/coordinator_base.html` nav with:

```django
<a class="sidebar-link{% if request.resolver_match.url_name == 'coordinator_participant_list' or request.resolver_match.url_name == 'coordinator_participant_detail' %} active{% endif %}" href="{% url 'coordinator_participant_list' %}">My Participants</a>
```

Create `templates/coordinators/sc_participant_list.html`:

```django
{% extends "coordinator_base.html" %}

{% block content %}
<div class="page-header">
  <div>
    <h1>My Participants</h1>
    <p>Participants currently assigned to you.</p>
  </div>
</div>
<div class="card">
  {% if participants %}
    <div class="list">
      {% for participant in participants %}
        <div class="list-item">
          <div>
            <strong>{{ participant.display_name }}</strong>
            <p>{{ participant.suburb }} {{ participant.state }} {{ participant.postcode }}</p>
          </div>
          <a class="button secondary" href="{% url 'coordinator_participant_detail' participant.id %}">View</a>
        </div>
      {% endfor %}
    </div>
  {% else %}
    <p class="muted">No assigned participants yet.</p>
  {% endif %}
</div>
{% endblock %}
```

Create `templates/coordinators/sc_participant_detail.html` with `display_name`, contact fields, address fields, `worker_visible_notes`, `address_access_instructions`, and `risk_safety_notes`. Exclude `internal_notes`.

- [ ] **Step 5: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorPortalParticipantTests
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add coordinators templates/coordinator_base.html templates/coordinators
git commit -m "Add support coordinator participant portal"
```

---

### Task 5: SC Coordination Log Submission

**Files:**
- Modify: `coordinators/forms.py`
- Modify: `coordinators/views.py`
- Modify: `coordinators/urls.py`
- Modify: `coordinators/tests.py`
- Modify: `templates/coordinator_base.html`
- Create: `templates/coordinators/sc_coordination_log_form.html`
- Create: `templates/coordinators/sc_coordination_log_list.html`
- Create: `templates/coordinators/sc_coordination_log_detail.html`

- [ ] **Step 1: Write failing submission tests**

Append to `coordinators/tests.py`:

```python
class CoordinatorLogSubmissionTests(TestCase):
    def setUp(self):
        self.coordinator = create_coordinator("coord-log")
        self.assigned = Participant.objects.create(
            first_name="Assigned",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        self.unassigned = Participant.objects.create(
            first_name="Hidden",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.assigned,
            coordinator=self.coordinator,
            start_date=date(2026, 9, 4),
        )
        self.client.force_login(self.coordinator.user)

    def valid_payload(self, participant):
        return {
            "participant": participant.id,
            "service_date": "2026-09-04",
            "start_time": "09:00",
            "end_time": "10:30",
            "break_minutes": "0",
            "actual_hours": "1.50",
            "coordination_type": CoordinationLog.CoordinationType.GENERAL,
            "case_notes": "Called provider and updated the participant plan notes.",
            "coordinator_notes": "Follow up again next week.",
        }

    def test_sc_can_submit_log_for_assigned_participant(self):
        response = self.client.post(
            reverse("coordinator_log_create"),
            self.valid_payload(self.assigned),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        log = CoordinationLog.objects.get(participant=self.assigned)
        self.assertEqual(log.coordinator, self.coordinator)
        self.assertEqual(log.status, CoordinationLog.Status.SUBMITTED)
        self.assertContains(response, "Coordination log submitted for admin review.")

    def test_sc_cannot_submit_log_for_unassigned_participant(self):
        response = self.client.post(
            reverse("coordinator_log_create"),
            self.valid_payload(self.unassigned),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CoordinationLog.objects.exists())
        self.assertContains(response, "Select a valid choice")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorLogSubmissionTests
```

Expected: FAIL because SC log forms and routes do not exist.

- [ ] **Step 3: Add SC log form**

Append to `coordinators/forms.py`:

```python
from .models import CoordinationLog
from .querysets import assigned_participants_for


class CoordinationLogForm(forms.ModelForm):
    class Meta:
        model = CoordinationLog
        fields = [
            "participant",
            "service_date",
            "start_time",
            "end_time",
            "break_minutes",
            "actual_hours",
            "coordination_type",
            "case_notes",
            "coordinator_notes",
        ]
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, coordinator=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.coordinator = coordinator
        self.fields["participant"].queryset = assigned_participants_for(coordinator)
```

- [ ] **Step 4: Add SC log views and routes**

Add to `coordinators/views.py`:

```python
from .forms import CoordinationLogForm
from .models import CoordinationLog


@coordinator_required
def coordinator_log_list(request):
    coordinator = get_current_coordinator(request.user)
    logs = CoordinationLog.objects.none()
    if coordinator:
        logs = CoordinationLog.objects.filter(coordinator=coordinator).select_related("participant")
    return render(
        request,
        "coordinators/sc_coordination_log_list.html",
        {"logs": logs},
    )


@coordinator_required
def coordinator_log_detail(request, log_id):
    coordinator = get_current_coordinator(request.user)
    log = get_object_or_404(
        CoordinationLog.objects.select_related("participant", "coordinator"),
        id=log_id,
        coordinator=coordinator,
    )
    return render(
        request,
        "coordinators/sc_coordination_log_detail.html",
        {"log": log},
    )


@coordinator_required
def coordinator_log_create(request):
    coordinator = get_current_coordinator(request.user)
    if request.method == "POST":
        form = CoordinationLogForm(request.POST, coordinator=coordinator)
        if form.is_valid():
            log = form.save(commit=False)
            log.coordinator = coordinator
            log.status = CoordinationLog.Status.SUBMITTED
            log.save()
            messages.success(request, "Coordination log submitted for admin review.")
            return redirect("coordinator_log_detail", log_id=log.id)
    else:
        form = CoordinationLogForm(coordinator=coordinator)
    return render(request, "coordinators/sc_coordination_log_form.html", {"form": form})
```

Extend `coordinators/urls.py`:

```python
path("sc/logs/", views.coordinator_log_list, name="coordinator_log_list"),
path("sc/logs/new/", views.coordinator_log_create, name="coordinator_log_create"),
path("sc/logs/<int:log_id>/", views.coordinator_log_detail, name="coordinator_log_detail"),
```

- [ ] **Step 5: Add templates and nav**

Update `templates/coordinator_base.html`:

```django
<a class="sidebar-link{% if request.resolver_match.url_name == 'coordinator_log_list' or request.resolver_match.url_name == 'coordinator_log_create' or request.resolver_match.url_name == 'coordinator_log_detail' %} active{% endif %}" href="{% url 'coordinator_log_list' %}">My Coordination Logs</a>
```

Create log form/list/detail templates using existing worker form patterns. On the list page, include a `Submit Coordination Log` button. On the detail page, show status and rejection reason when rejected.

- [ ] **Step 6: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorLogSubmissionTests
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add coordinators templates/coordinator_base.html templates/coordinators
git commit -m "Add support coordinator log submission"
```

---

### Task 6: Admin Coordination Log Review

**Files:**
- Modify: `coordinators/views.py`
- Modify: `coordinators/urls.py`
- Modify: `coordinators/tests.py`
- Create: `templates/coordinators/coordination_log_list.html`
- Create: `templates/coordinators/coordination_log_detail.html`
- Modify: `templates/admin_base.html`
- Modify: `core/models.py`

- [ ] **Step 1: Write failing review tests**

Append to `coordinators/tests.py`:

```python
class CoordinationLogAdminReviewTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="admin-review",
            password="pass12345",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN,
        )
        self.coordinator = create_coordinator("coord-review")
        self.participant = Participant.objects.create(
            first_name="Review",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        self.log = CoordinationLog.objects.create(
            participant=self.participant,
            coordinator=self.coordinator,
            service_date=date(2026, 9, 4),
            start_time=time(9, 0),
            end_time=time(10, 30),
            break_minutes=0,
            actual_hours=Decimal("1.50"),
            coordination_type=CoordinationLog.CoordinationType.GENERAL,
            case_notes="Submitted coordination work.",
        )
        self.client.force_login(self.admin_user)

    def test_admin_can_approve_submitted_coordination_log(self):
        response = self.client.post(
            reverse("coordination_log_approve", args=[self.log.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.APPROVED)
        self.assertEqual(self.log.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.log.reviewed_at)
        self.assertContains(response, "Coordination log approved.")

    def test_admin_reject_requires_reason(self):
        response = self.client.post(
            reverse("coordination_log_reject", args=[self.log.id]),
            {"rejection_reason": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.SUBMITTED)
        self.assertContains(response, "Rejection reason is required.")

    def test_admin_can_reject_submitted_coordination_log(self):
        response = self.client.post(
            reverse("coordination_log_reject", args=[self.log.id]),
            {"rejection_reason": "Needs more detail."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.REJECTED)
        self.assertEqual(self.log.rejection_reason, "Needs more detail.")
        self.assertContains(response, "Coordination log rejected.")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinationLogAdminReviewTests
```

Expected: FAIL because admin review routes do not exist.

- [ ] **Step 3: Add admin review views and routes**

Add to `coordinators/views.py`:

```python
from django.utils import timezone
from django.views.decorators.http import require_POST


@admin_required
def coordination_log_list(request):
    logs = CoordinationLog.objects.select_related("participant", "coordinator")
    status = request.GET.get("status", "").strip()
    if status:
        logs = logs.filter(status=status)
    return render(
        request,
        "coordinators/coordination_log_list.html",
        {
            "logs": logs,
            "status": status,
            "status_choices": CoordinationLog.Status.choices,
        },
    )


@admin_required
def coordination_log_detail(request, log_id):
    log = get_object_or_404(
        CoordinationLog.objects.select_related("participant", "coordinator", "reviewed_by"),
        id=log_id,
    )
    return render(request, "coordinators/coordination_log_detail.html", {"log": log})


@admin_required
@require_POST
def coordination_log_approve(request, log_id):
    log = get_object_or_404(
        CoordinationLog,
        id=log_id,
        status=CoordinationLog.Status.SUBMITTED,
    )
    log.status = CoordinationLog.Status.APPROVED
    log.reviewed_by = request.user
    log.reviewed_at = timezone.now()
    log.rejection_reason = ""
    log.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])
    messages.success(request, "Coordination log approved.")
    return redirect("coordination_log_detail", log_id=log.id)


@admin_required
@require_POST
def coordination_log_reject(request, log_id):
    log = get_object_or_404(
        CoordinationLog,
        id=log_id,
        status=CoordinationLog.Status.SUBMITTED,
    )
    rejection_reason = request.POST.get("rejection_reason", "").strip()
    if not rejection_reason:
        messages.error(request, "Rejection reason is required.")
        return redirect("coordination_log_detail", log_id=log.id)
    log.status = CoordinationLog.Status.REJECTED
    log.reviewed_by = request.user
    log.reviewed_at = timezone.now()
    log.rejection_reason = rejection_reason
    log.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])
    messages.success(request, "Coordination log rejected.")
    return redirect("coordination_log_detail", log_id=log.id)
```

Extend `coordinators/urls.py`:

```python
path("coordination-logs/", views.coordination_log_list, name="coordination_log_list"),
path("coordination-logs/<int:log_id>/", views.coordination_log_detail, name="coordination_log_detail"),
path("coordination-logs/<int:log_id>/approve/", views.coordination_log_approve, name="coordination_log_approve"),
path("coordination-logs/<int:log_id>/reject/", views.coordination_log_reject, name="coordination_log_reject"),
```

- [ ] **Step 4: Add admin templates and nav**

Create list and detail templates with existing `service_logs` review patterns. The detail page must include approve/reject forms only when status is `submitted`.

Update `templates/admin_base.html` Operations nav:

```django
<a class="sidebar-link{% if request.resolver_match.url_name == 'coordination_log_list' or request.resolver_match.url_name == 'coordination_log_detail' %} active{% endif %}" href="{% url 'coordination_log_list' %}">Coordination Logs</a>
```

- [ ] **Step 5: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinationLogAdminReviewTests
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add coordinators templates/admin_base.html templates/coordinators core/models.py
git commit -m "Add admin coordination log review"
```

---

### Task 7: Audit Logs And UI Polish

**Files:**
- Modify: `core/models.py`
- Modify: `coordinators/views.py`
- Modify: `coordinators/tests.py`
- Modify: `static/css/app.css`
- Modify: `templates/coordinator_base.html`
- Modify: `templates/coordinators/*.html`

- [ ] **Step 1: Write failing audit tests**

Append to `coordinators/tests.py`:

```python
from core.models import AuditLog


class CoordinatorAuditTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="admin-audit",
            password="pass12345",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN,
        )
        self.coordinator = create_coordinator("coord-audit")
        self.participant = Participant.objects.create(
            first_name="Audit",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )

    def test_coordination_log_submission_writes_audit_log(self):
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.participant,
            coordinator=self.coordinator,
            start_date=date(2026, 9, 4),
        )
        self.client.force_login(self.coordinator.user)

        self.client.post(
            reverse("coordinator_log_create"),
            {
                "participant": self.participant.id,
                "service_date": "2026-09-04",
                "start_time": "09:00",
                "end_time": "10:30",
                "break_minutes": "0",
                "actual_hours": "1.50",
                "coordination_type": CoordinationLog.CoordinationType.GENERAL,
                "case_notes": "Audit-covered coordination work.",
                "coordinator_notes": "",
            },
        )

        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.coordinator.user,
                action=AuditLog.Action.COORDINATION_LOG_SUBMITTED,
            ).exists()
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorAuditTests
```

Expected: FAIL because coordinator audit actions are not defined or not written.

- [ ] **Step 3: Add audit actions and write audit logs**

Add choices to `core/models.py` `AuditLog.Action`:

```python
SUPPORT_COORDINATOR_CREATED = "support_coordinator_created", "Support coordinator created"
SUPPORT_COORDINATOR_UPDATED = "support_coordinator_updated", "Support coordinator updated"
PARTICIPANT_COORDINATOR_ASSIGNED = "participant_coordinator_assigned", "Participant assigned to support coordinator"
COORDINATION_LOG_SUBMITTED = "coordination_log_submitted", "Coordination log submitted"
COORDINATION_LOG_APPROVED = "coordination_log_approved", "Coordination log approved"
COORDINATION_LOG_REJECTED = "coordination_log_rejected", "Coordination log rejected"
```

In `coordinators/views.py`, import:

```python
from core.audit import write_audit_log
from core.models import AuditLog
```

Write audit logs after successful create, assign, submit, approve, and reject actions:

```python
write_audit_log(
    request.user,
    AuditLog.Action.COORDINATION_LOG_SUBMITTED,
    log,
    f"Submitted coordination log {log.id}.",
)
```

Use matching action names and object references for the other actions.

- [ ] **Step 4: Add focused UI polish**

Use existing CSS tokens and keep additions small:

```css
.coordinator-summary-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}

.coordinator-log-actions {
  display: flex;
  gap: 0.65rem;
  flex-wrap: wrap;
}

@media (max-width: 760px) {
  .coordinator-summary-grid {
    grid-template-columns: 1fr;
  }

  .coordinator-log-actions,
  .coordinator-log-actions form,
  .coordinator-log-actions button,
  .coordinator-log-actions .button {
    width: 100%;
  }
}
```

Confirm SC mobile templates keep tap targets at least 44px high by using existing `.button`, `.card-action`, and `.sidebar-link` classes.

- [ ] **Step 5: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators.tests.CoordinatorAuditTests coordinators.tests
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add core/models.py coordinators static/css/app.css templates/coordinator_base.html templates/coordinators
git commit -m "Add coordinator audit logs and polish"
```

---

### Task 8: Full Regression And Safety Check

**Files:**
- Verify all modified files.
- No new feature files beyond the coordinator scope.

- [ ] **Step 1: Run full coordinator tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test coordinators
```

Expected: all coordinator tests pass.

- [ ] **Step 2: Run existing business-chain tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test accounts.tests workers.tests participants.tests participants.tests_assignments scheduling.tests_shifts service_logs.tests_review service_logs.tests_service_logs invoices.tests_invoices documents.tests_documents core.tests_dashboards
```

Expected: all selected regression tests pass.

- [ ] **Step 3: Run project checks**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
git diff --check
```

Expected:

- `System check identified no issues`
- `No changes detected`
- `git diff --check` exits with code 0, allowing only existing line-ending warnings if they appear

- [ ] **Step 4: Manual smoke test**

Run the local server:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Check:

- Admin can open Support Coordinators.
- Admin can create an SC.
- Admin can assign a participant.
- SC login redirects to SC dashboard.
- SC sees assigned participant only.
- SC submits a coordination log.
- Admin can approve and reject coordination logs.
- Existing SW dashboard, My Shifts, My Logs, service log submission, admin Service Logs, roster, and invoices still load.

- [ ] **Step 5: Final commit or amend**

If verification required small fixes, stage only SC V1 paths and commit them:

```powershell
git add accounts bscare_ndis coordinators core/models.py static/css/app.css templates/admin_base.html templates/coordinator_base.html templates/coordinators
git commit -m "Stabilize support coordinator v1"
```

If no fixes are needed, leave history as the task commits above.
