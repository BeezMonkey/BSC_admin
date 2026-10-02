# Admin Mobile Inset Swipe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Safari-conflicting screen-edge Admin gesture with an inset gesture that moves the complete mobile Admin surface and reveals the drawer underneath.

**Architecture:** Wrap the mobile header and Admin content in a foreground `.admin-mobile-surface`, leave the navigation drawer fixed beneath it, and drive the surface translation from the existing single drawer controller. Gesture tracking starts only in a safe inset lane, excludes interactive and horizontally scrollable targets, and preserves vertical scrolling until horizontal intent is clear.

**Tech Stack:** Django templates and `SimpleTestCase`, CSS media queries/transforms, vanilla JavaScript Pointer Events, Node syntax validation, mobile browser verification.

---

## File Structure

- Modify `core/tests_admin_appearance.py`: assert the production shell uses a mobile surface and no longer renders the edge zone.
- Modify `core/tests_theme.py`: assert the CSS/JavaScript contract for inset gesture safety and surface movement.
- Modify `templates/admin_base.html`: add the foreground surface wrapper and move the backdrop into it.
- Modify `static/css/admin.css`: make the drawer the stationary lower layer and the mobile surface the translated upper layer.
- Modify `static/js/admin_nav.js`: track inset surface gestures and animate the surface instead of the drawer.

### Task 1: Lock The New Structure And Gesture Contract With Failing Tests

**Files:**
- Modify: `core/tests_admin_appearance.py`
- Modify: `core/tests_theme.py`

- [ ] **Step 1: Replace the old shell expectation**

Update `test_admin_shell_includes_mobile_navigation` to require the new surface and reject the obsolete edge zone:

```python
self.assertIn('class="admin-mobile-surface"', html)
self.assertNotIn('class="admin-edge-swipe-zone"', html)
```

- [ ] **Step 2: Replace the old asset expectations**

Update `test_admin_mobile_navigation_assets_exist` with the new safety contract:

```python
self.assertIn(".admin-mobile-surface", css)
self.assertNotIn(".admin-edge-swipe-zone", css)
self.assertIn("const INSET_START = 32;", script)
self.assertIn("const INSET_END = 112;", script)
self.assertIn("const INTENT_DISTANCE = 12;", script)
self.assertIn("isIgnoredGestureTarget", script)
self.assertIn('closest("a, button, input, select, textarea, summary', script)
self.assertIn('{ passive: false }', script)
self.assertNotIn("const EDGE_ZONE", script)
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
python manage.py test core.tests_admin_appearance core.tests_theme --verbosity 1
```

Expected: failures identify the missing `.admin-mobile-surface`, the still-present edge zone, and missing inset constants.

- [ ] **Step 4: Commit the failing tests**

```powershell
git add core/tests_admin_appearance.py core/tests_theme.py
git commit -m "test: define admin inset swipe behavior"
```

### Task 2: Move The Mobile Page Into A Foreground Surface

**Files:**
- Modify: `templates/admin_base.html`
- Modify: `static/css/admin.css`

- [ ] **Step 1: Replace the edge zone with a surface wrapper**

Keep the desktop sidebar and drawer as siblings. Wrap the existing mobile header, backdrop, and content as follows:

```html
<div class="app-shell" data-admin-theme>
  <aside class="sidebar">...</aside>
  <aside class="admin-mobile-drawer" id="admin-mobile-drawer" ...>...</aside>
  <div class="admin-mobile-surface">
    <header class="admin-mobile-header">...</header>
    <button class="admin-mobile-drawer-backdrop" ... hidden></button>
    <section class="content">...</section>
  </div>
</div>
```

Do not change navigation URLs, active-state conditions, logout behavior, messages, or `{% block content %}`.

- [ ] **Step 2: Define desktop-neutral and mobile-layer styling**

Use `display: contents` by default so desktop grid children retain their existing placement. At `max-width: 760px`, make the wrapper a foreground surface:

```css
[data-admin-theme] .admin-mobile-surface {
  display: contents;
}

@media (max-width: 760px) {
  [data-admin-theme] .admin-mobile-surface {
    position: relative;
    z-index: 70;
    display: block;
    min-width: 0;
    min-height: 100dvh;
    background: var(--surface);
    transform: translate3d(0, 0, 0);
    transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1), border-radius 220ms ease, box-shadow 220ms ease;
    will-change: transform;
  }
}
```

- [ ] **Step 3: Keep the drawer below and move the surface when open**

Define one shared drawer width and apply it to both the drawer and surface translation:

```css
[data-admin-theme] {
  --admin-mobile-drawer-width: min(84vw, 320px);
}

@media (max-width: 760px) {
  [data-admin-theme] .admin-mobile-drawer {
    z-index: 60;
    width: var(--admin-mobile-drawer-width);
    transform: none;
  }

  body.admin-nav-open [data-admin-theme] .admin-mobile-surface {
    border-radius: 22px 0 0 22px;
    box-shadow: -10px 0 28px rgba(15, 23, 42, 0.18);
    transform: translate3d(var(--admin-mobile-drawer-width), 0, 0);
  }
}
```

Make the backdrop absolute within the surface so it moves with the content and intercepts taps only while open. Update reduced-motion and dragging selectors to target the surface and backdrop.

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
python manage.py test core.tests_admin_appearance core.tests_theme --verbosity 1
```

Expected: shell/CSS assertions pass; JavaScript assertions remain red until Task 3.

### Task 3: Replace Edge Tracking With Inset Surface Tracking

**Files:**
- Modify: `static/js/admin_nav.js`

- [ ] **Step 1: Replace edge dependencies and constants**

Query `.admin-mobile-surface`, remove `.admin-edge-swipe-zone`, and define:

```javascript
const INSET_START = 32;
const INSET_END = 112;
const INTENT_DISTANCE = 12;
```

The controller must return early if the surface is missing.

- [ ] **Step 2: Exclude interactive and horizontal-scroll targets**

Add one target guard:

```javascript
function isIgnoredGestureTarget(target) {
  if (!(target instanceof Element)) {
    return false;
  }
  return Boolean(target.closest(
    "a, button, input, select, textarea, summary, [contenteditable], .table-wrap, [data-admin-swipe-ignore]"
  ));
}
```

For opening only, require `clientX >= INSET_START`, `clientX <= INSET_END`, and a target that is not ignored. The first 32px therefore remains available to Safari.

- [ ] **Step 3: Translate the surface during drag**

Replace drawer translation with pixel-based surface translation:

```javascript
surface.style.transform = "translate3d(" + (state.progress * drawerWidth()) + "px, 0, 0)";
backdrop.style.opacity = String(state.progress);
```

Clear the surface's inline transform after settling. Keep the existing open ratio, close ratio, velocity threshold, cancellation behavior, focus handling, body scroll lock, Escape support, and desktop reset.

- [ ] **Step 4: Bind pointer tracking to the surface**

Use one pointer source for both directions:

```javascript
surface.addEventListener("pointerdown", function (event) {
  beginTracking(event, state.open ? "close" : "open");
});
surface.addEventListener("pointermove", updateDrag, { passive: false });
surface.addEventListener("pointerup", finishTracking);
surface.addEventListener("pointercancel", cancelTracking);
```

Suppress the backdrop click generated after a real close drag so an incomplete drag can settle open without an immediate click closing it. A simple backdrop tap must still close normally.

- [ ] **Step 5: Run focused tests and JavaScript syntax validation**

Run:

```powershell
python manage.py test core.tests_admin_appearance core.tests_theme --verbosity 1
node --check static/js/admin_nav.js
```

Expected: all focused tests pass and Node reports no syntax errors.

- [ ] **Step 6: Commit the implementation**

```powershell
git add templates/admin_base.html static/css/admin.css static/js/admin_nav.js
git commit -m "fix: move admin drawer gesture away from Safari edge"
```

### Task 4: Verify Interaction And Regression Safety

**Files:**
- Modify: `docs/superpowers/plans/2026-10-02-admin-mobile-inset-swipe.md`

- [ ] **Step 1: Run repository checks**

```powershell
python manage.py collectstatic --noinput --verbosity 0
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check origin/staging...HEAD
```

Expected: no issues, no migrations, and no whitespace errors.

- [ ] **Step 2: Run the full Django suite**

```powershell
python manage.py test --verbosity 1
```

Expected: all tests pass.

- [ ] **Step 3: Verify mobile behavior in a local browser**

At approximately 390x844, verify:

- hamburger opens the same drawer;
- right drag beginning inside 32-112px moves the complete page surface;
- movement beginning inside the first 32px does not start the application gesture;
- vertical drag and interactive controls do not open the drawer;
- incomplete drag settles closed;
- backdrop tap, close button, Escape, and left drag close the drawer;
- drawer navigation scrolls independently;
- resizing above 760px restores the unchanged desktop layout.

- [ ] **Step 4: Record completion and commit**

Mark completed steps in this plan, then run:

```powershell
git add docs/superpowers/plans/2026-10-02-admin-mobile-inset-swipe.md
git commit -m "docs: record admin inset swipe verification"
```

- [ ] **Step 5: Push and open a staging PR**

Push `codex/admin-mobile-inset-swipe` and open a PR with base `staging`. State clearly that iPhone Safari remains the final acceptance environment and `main` is unchanged.
