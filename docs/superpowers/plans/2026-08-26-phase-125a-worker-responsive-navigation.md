# Phase 125A Worker Responsive Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Support Worker portal navigation work cleanly across desktop, medium-width, and phone-sized screens without changing worker business workflows.

**Architecture:** Keep the worker portal on the existing `worker_base.html` shell. Add a menu trigger and drawer navigation that reuse the same existing worker URLs for medium and phone widths, while desktop keeps the existing sidebar. Preserve the approved worker content layout direction; this phase changes navigation behavior, not worker business content. Add small vanilla JavaScript only for opening/closing the drawer.

**Tech Stack:** Django templates, Django test client, static CSS, vanilla JavaScript.

---

## File Structure

- Modify `templates/worker_base.html`
  - Add reusable worker navigation markup.
  - Add mobile menu trigger and drawer.
  - Keep existing sidebar links and logout POST form behavior.

- Modify `static/css/app.css`
  - Replace worker medium/phone horizontal scrolling nav with drawer navigation.
  - Keep desktop sidebar behavior.
  - Preserve current card/content styling.

- Create `static/js/worker_nav.js`
  - Toggle drawer open/closed.
  - Close with close button, backdrop, Escape key.
  - Return focus to the menu button.

- Modify `core/tests_theme.py`
  - Assert CSS and JS hooks exist.

- Modify `core/tests_dashboards.py`
  - Assert worker shell still exposes current worker URLs and logout POST form.
  - Assert worker dashboard content remains present.

---

### Task 1: Add UI Contract Tests

**Files:**
- Modify: `core/tests_theme.py`
- Modify: `core/tests_dashboards.py`

- [ ] **Step 1: Add CSS/JS hook assertions to `core/tests_theme.py`**

Add this test method to `ThemeTokenTests`:

```python
def test_worker_responsive_navigation_assets_exist(self):
    css = Path("static/css/app.css").read_text(encoding="utf-8")
    script = Path("static/js/worker_nav.js").read_text(encoding="utf-8")

    self.assertIn(".worker-mobile-menu-button", css)
    self.assertIn(".worker-mobile-drawer", css)
    self.assertIn(".worker-mobile-drawer-backdrop", css)
    self.assertIn(".worker-nav-open", css)
    self.assertIn("@media (max-width: 980px)", css)
    self.assertIn("overflow-x: visible;", css)
    self.assertIn("worker-mobile-menu-button", script)
    self.assertIn("worker-nav-open", script)
    self.assertIn("Escape", script)
```

- [ ] **Step 2: Add worker shell assertions to `core/tests_dashboards.py`**

Extend `DashboardPolishTests.test_worker_dashboard_uses_worker_responsive_layout_hooks` so it also checks:

```python
self.assertContains(response, 'class="worker-mobile-menu-button"')
self.assertContains(response, 'class="worker-mobile-drawer"')
self.assertContains(response, 'aria-label="Worker menu"')
self.assertContains(response, 'href="/sw/dashboard/"')
self.assertContains(response, 'href="/sw/shifts/"')
self.assertContains(response, 'href="/sw/logs/"')
self.assertContains(response, 'href="/sw/documents/"')
self.assertContains(response, 'href="/sw/profile/"')
self.assertContains(response, 'method="post" action="/logout/"')
```

- [ ] **Step 3: Run focused tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_theme core.tests_dashboards
```

Expected: fails because `static/js/worker_nav.js`, drawer markup, and CSS hooks do not exist yet.

---

### Task 2: Update Worker Shell Markup

**Files:**
- Modify: `templates/worker_base.html`

- [ ] **Step 1: Add a compact worker header before the existing sidebar**

Add a medium/phone header inside `.worker-app-shell` before `<aside class="sidebar worker-sidebar">`:

```django
<header class="worker-mobile-header">
  <button class="worker-mobile-menu-button" type="button" aria-label="Open worker menu" aria-controls="worker-mobile-drawer" aria-expanded="false">
    <span aria-hidden="true"></span>
  </button>
  <div>
    <div class="worker-mobile-brand">Brisbane Star Care</div>
    <div class="worker-mobile-role">Support Worker</div>
  </div>
  <span class="worker-mobile-user">{{ request.user.get_username }}</span>
</header>
```

- [ ] **Step 2: Add drawer navigation after the existing sidebar**

Add this drawer markup after the existing `</aside>`:

```django
<div class="worker-mobile-drawer-backdrop" data-worker-menu-close hidden></div>
<aside class="worker-mobile-drawer" id="worker-mobile-drawer" aria-label="Worker menu" hidden>
  <div class="worker-mobile-drawer-header">
    <div>
      <div class="worker-mobile-brand">Brisbane Star Care</div>
      <div class="worker-mobile-role">{{ request.user.get_username }}</div>
    </div>
    <button class="worker-mobile-close-button" type="button" aria-label="Close worker menu" data-worker-menu-close>&times;</button>
  </div>
  <nav class="worker-mobile-drawer-nav" aria-label="Worker navigation">
    <a class="sidebar-link{% if request.resolver_match.url_name == 'worker_dashboard' %} active{% endif %}" href="{% url 'worker_dashboard' %}">Dashboard</a>
    <a class="sidebar-link{% if request.resolver_match.url_name == 'worker_shift_list' or request.resolver_match.url_name == 'worker_shift_detail' %} active{% endif %}" href="{% url 'worker_shift_list' %}">My Shifts</a>
    <a class="sidebar-link{% if request.resolver_match.url_name == 'worker_log_list' or request.resolver_match.url_name == 'worker_service_log_create' or request.resolver_match.url_name == 'worker_service_log_detail' %} active{% endif %}" href="{% url 'worker_log_list' %}">My Logs</a>
    <a class="sidebar-link{% if request.resolver_match.url_name == 'worker_document_list' or request.resolver_match.url_name == 'worker_document_detail' %} active{% endif %}" href="{% url 'worker_document_list' %}">Documents</a>
    <a class="sidebar-link{% if request.resolver_match.url_name == 'worker_profile' %} active{% endif %}" href="{% url 'worker_profile' %}">Profile</a>
  </nav>
  <form class="worker-mobile-logout" method="post" action="{% url 'logout' %}">
    {% csrf_token %}
    <button class="button secondary" type="submit">Logout</button>
  </form>
</aside>
```

- [ ] **Step 3: Load `worker_nav.js` only for worker pages**

Before `{% endblock %}`, add:

```django
<script src="{% static 'js/worker_nav.js' %}" defer></script>
```

If `worker_base.html` does not already load `{% static %}`, add `{% load static %}` at the top of the file.

- [ ] **Step 4: Run worker dashboard tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_dashboards
```

Expected: some assertions pass, CSS/JS hook tests still fail until later tasks.

- [ ] **Step 5: Commit**

```powershell
git add templates/worker_base.html core/tests_dashboards.py core/tests_theme.py
git commit -m "test: define worker responsive navigation contract"
```

---

### Task 3: Add Drawer JavaScript

**Files:**
- Create: `static/js/worker_nav.js`

- [ ] **Step 1: Create `static/js/worker_nav.js`**

```javascript
(function () {
  const menuButton = document.querySelector(".worker-mobile-menu-button");
  const drawer = document.querySelector(".worker-mobile-drawer");
  const backdrop = document.querySelector(".worker-mobile-drawer-backdrop");
  const closeButtons = document.querySelectorAll("[data-worker-menu-close]");

  if (!menuButton || !drawer || !backdrop) {
    return;
  }

  function openMenu() {
    drawer.hidden = false;
    backdrop.hidden = false;
    document.body.classList.add("worker-nav-open");
    menuButton.setAttribute("aria-expanded", "true");
    const firstLink = drawer.querySelector("a, button");
    if (firstLink) {
      firstLink.focus();
    }
  }

  function closeMenu() {
    drawer.hidden = true;
    backdrop.hidden = true;
    document.body.classList.remove("worker-nav-open");
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.focus();
  }

  menuButton.addEventListener("click", openMenu);

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeMenu);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !drawer.hidden) {
      closeMenu();
    }
  });
})();
```

- [ ] **Step 2: Run asset tests and verify CSS assertions still fail**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_theme
```

Expected: fails only for missing CSS hooks.

- [ ] **Step 3: Commit**

```powershell
git add static/js/worker_nav.js
git commit -m "feat: add worker mobile navigation drawer script"
```

---

### Task 4: Add Responsive Worker Navigation CSS

**Files:**
- Modify: `static/css/app.css`

- [ ] **Step 1: Add base hidden mobile navigation styles near existing worker CSS**

Add near the `.worker-app-shell` section:

```css
.worker-mobile-header,
.worker-mobile-drawer,
.worker-mobile-drawer-backdrop {
  display: none;
}

.worker-mobile-menu-button,
.worker-mobile-close-button {
  border: 1px solid var(--line);
  border-radius: 7px;
  background: #ffffff;
  color: var(--ink);
  font-weight: var(--weight-action);
}
```

- [ ] **Step 2: Replace worker horizontal nav behavior inside `@media (max-width: 980px)`**

Find the existing worker mobile rules where `.worker-sidebar-nav` uses flex and `overflow-x: auto`. Replace the worker-specific portion with drawer behavior that applies to medium and phone widths:

```css
.worker-mobile-header {
  position: sticky;
  top: 0;
  z-index: 30;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.7rem;
  border-bottom: 1px solid var(--line);
  padding: 0.8rem 1rem;
  background: #ffffff;
}

.worker-mobile-brand {
  color: var(--ink);
  font-size: 1rem;
  font-weight: var(--weight-heading);
  line-height: 1.15;
}

.worker-mobile-role,
.worker-mobile-user {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: var(--weight-label);
  line-height: 1.2;
}

.worker-mobile-user {
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.worker-mobile-menu-button {
  display: inline-grid;
  place-items: center;
  width: 2.55rem;
  height: 2.55rem;
  padding: 0;
}

.worker-mobile-menu-button::before,
.worker-mobile-menu-button::after,
.worker-mobile-menu-button span {
  content: "";
  display: block;
  width: 1.25rem;
  height: 0.16rem;
  border-radius: 999px;
  background: var(--ink);
}

.worker-mobile-menu-button span {
  margin: 0.22rem 0;
  width: 0.95rem;
  background: var(--brand);
}

.worker-sidebar {
  display: none;
}

.worker-mobile-drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: block;
  background: rgba(15, 23, 42, 0.45);
}

.worker-mobile-drawer-backdrop[hidden],
.worker-mobile-drawer[hidden] {
  display: none;
}

.worker-mobile-drawer {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 50;
  display: grid;
  align-content: start;
  width: min(19rem, 86vw);
  border-right: 1px solid var(--line);
  border-radius: 0 12px 12px 0;
  padding: 1rem;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
}

.worker-mobile-drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0.9rem;
}

.worker-mobile-close-button {
  width: 2.35rem;
  height: 2.35rem;
  padding: 0;
  font-size: 1.25rem;
  line-height: 1;
}

.worker-mobile-drawer-nav {
  display: grid;
  gap: 0.35rem;
  padding: 0.9rem 0;
}

.worker-mobile-drawer-nav .sidebar-link {
  color: var(--ink);
}

.worker-mobile-drawer-nav .sidebar-link.active {
  color: var(--sidebar-active-text);
}

.worker-mobile-logout {
  border-top: 1px solid var(--line);
  padding-top: 0.9rem;
}

.worker-mobile-logout .button {
  width: 100%;
}

body.worker-nav-open {
  overflow: hidden;
}
```

- [ ] **Step 3: Keep desktop sidebar and content stable above drawer breakpoint**

Add a small desktop/large-tablet guard before the drawer breakpoint if needed:

```css
@media (min-width: 981px) {
  .worker-app-shell {
    grid-template-columns: 290px minmax(0, 1fr);
  }
}
```

- [ ] **Step 4: Run CSS tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_theme
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add static/css/app.css
git commit -m "style: add worker responsive navigation shell"
```

---

### Task 5: Full Verification And Manual Browser Check

**Files:**
- Verify only.

- [ ] **Step 1: Run automated tests**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests_theme core.tests_dashboards accounts.tests scheduling.tests_shifts service_logs.tests_service_logs
.\.venv\Scripts\python.exe manage.py check
```

Expected: all tests pass and system check reports no issues.

- [ ] **Step 2: Start local server if needed**

Run:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Expected: local site opens at `http://127.0.0.1:8000/`.

- [ ] **Step 3: Manual desktop check**

Open:

```text
http://127.0.0.1:8000/sw/dashboard/
```

Expected:

- desktop sidebar remains visible
- worker dashboard summary and cards remain visually similar
- worker page links work

- [ ] **Step 4: Manual medium-width check**

Resize browser to a medium width around 760-980px.

Expected:

- compact menu button appears instead of horizontal scrolling tabs
- drawer opens with existing worker destinations
- content remains stable and not clipped

- [ ] **Step 5: Manual phone-width check**

Resize browser to about 390px.

Expected:

- top-left menu button appears
- desktop sidebar is hidden
- tapping menu opens drawer
- drawer links go to Dashboard, My Shifts, My Logs, Documents, and Profile
- drawer Logout is visible and remains a POST form
- closing drawer via close button and Escape works

- [ ] **Step 6: Final status**

Run:

```powershell
git status --short --branch
```

Expected: only unrelated pre-existing untracked files remain outside this phase.
