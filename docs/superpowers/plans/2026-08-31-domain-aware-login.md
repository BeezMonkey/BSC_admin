# Domain-Aware Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show different login page labels for the admin and support worker domains while preserving the existing shared authentication, role redirects, and permissions.

**Architecture:** The login view derives display metadata from the request host and passes it to the existing login template. Authentication remains Django's `LoginView`, and post-login routing remains `role_redirect`.

**Tech Stack:** Django class-based auth views, Django templates, Django test client.

---

### Task 1: Lock Domain Login Branding With Tests

**Files:**
- Modify: `accounts/tests.py`

- [ ] **Step 1: Write failing tests**

```python
class LoginBrandingTests(TestCase):
    allowed_hosts = ["testserver", "admin.bscare.com.au", "sw.bscare.com.au"]

    @override_settings(ALLOWED_HOSTS=allowed_hosts)
    def test_admin_domain_shows_admin_portal_label(self):
        response = self.client.get(reverse("login"), HTTP_HOST="admin.bscare.com.au")

        self.assertContains(response, "NDIS Admin Portal")
        self.assertContains(response, "Login to Admin Portal")

    @override_settings(ALLOWED_HOSTS=allowed_hosts)
    def test_support_worker_domain_shows_worker_portal_label(self):
        response = self.client.get(reverse("login"), HTTP_HOST="sw.bscare.com.au")

        self.assertContains(response, "Support Worker Portal")
        self.assertContains(response, "Login to Worker Portal")

    @override_settings(ALLOWED_HOSTS=allowed_hosts)
    def test_default_host_keeps_existing_generic_label(self):
        response = self.client.get(reverse("login"), HTTP_HOST="testserver")

        self.assertContains(response, "NDIS Admin System")
        self.assertContains(response, ">Login</button>")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe manage.py test accounts.tests.LoginBrandingTests`

Expected: FAIL because the login view still renders the fixed `NDIS Admin System` and `Login` copy for every host.

### Task 2: Add Host-Based Login Context

**Files:**
- Modify: `accounts/views.py`
- Modify: `templates/accounts/login.html`

- [ ] **Step 1: Implement minimal view context**

```python
class BSCLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        host = self.request.get_host().split(":", 1)[0].lower()
        context.update(get_login_portal_context(host))
        return context
```

- [ ] **Step 2: Keep role redirect unchanged**

Do not modify `role_redirect`, `ADMIN_ROLES`, `SUPPORT_WORKER`, login URL settings, or access decorators.

- [ ] **Step 3: Render template variables**

```django
<p>{{ portal_name|default:"NDIS Admin System" }}</p>
<button type="submit">{{ login_button_label|default:"Login" }}</button>
```

- [ ] **Step 4: Run focused tests**

Run: `.venv\Scripts\python.exe manage.py test accounts.tests`

Expected: PASS, including existing role routing and access tests.

### Task 3: Verify Project Health

**Files:**
- Verify only.

- [ ] **Step 1: Run Django check**

Run: `.venv\Scripts\python.exe manage.py check`

Expected: `System check identified no issues`.

- [ ] **Step 2: Inspect diff**

Run: `git diff -- accounts/views.py templates/accounts/login.html accounts/tests.py docs/superpowers/plans/2026-08-31-domain-aware-login.md`

Expected: Only domain-aware login display and test/plan changes.
