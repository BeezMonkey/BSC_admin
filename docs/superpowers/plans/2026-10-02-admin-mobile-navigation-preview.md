# Admin Mobile Navigation Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone mobile Admin dashboard preview with the existing Support Worker-style hamburger drawer plus a safe ChatGPT-style edge swipe gesture.

**Architecture:** Add one self-contained HTML file containing preview-only markup, styles, and JavaScript. A small drawer controller owns open/closed state, pointer gesture intent, thresholds, accessibility attributes, and cleanup; no production templates or assets are imported or changed.

**Tech Stack:** HTML5, CSS, vanilla JavaScript Pointer Events, Codex in-app browser verification.

---

## File Structure

- Create `docs/prototypes/admin-mobile-navigation-demo.html`: complete isolated preview, responsive styling, drawer controller, realistic dashboard content, and visible interaction guidance.
- No production file is modified.

### Task 1: Build the standalone mobile navigation preview

**Files:**
- Create: `docs/prototypes/admin-mobile-navigation-demo.html`

- [x] **Step 1: Create the semantic mobile shell and drawer**

Use a fixed mobile header, a backdrop, and one left drawer controlled by both the hamburger button and edge gesture. Keep the Admin navigation order and labels identical to production:

```html
<header class="mobile-header">
  <button class="menu-button" type="button" aria-label="Open Admin menu"
          aria-controls="admin-drawer" aria-expanded="false">
    <span class="menu-icon" aria-hidden="true"></span>
  </button>
  <div class="mobile-identity">
    <strong>BSC Admin</strong>
    <span>Administration</span>
  </div>
</header>
<div class="drawer-backdrop" hidden></div>
<aside class="mobile-drawer" id="admin-drawer" aria-label="Admin menu" hidden>
  <header class="drawer-header">
    <div><strong>Brisbane Star Care</strong><span>NDIS Admin</span></div>
    <button class="close-button" type="button" aria-label="Close Admin menu">&times;</button>
  </header>
  <nav aria-label="Admin navigation">
    <span class="section-label">Operations</span>
    <a class="nav-link active" href="#dashboard">Dashboard</a>
    <a class="nav-link" href="#participants">Participants</a>
    <a class="nav-link" href="#workers">Support Workers</a>
    <a class="nav-link" href="#roster">Roster</a>
    <a class="nav-link" href="#logs">Service Logs</a>
    <a class="nav-link" href="#cancellations">Cancellations</a>
    <span class="section-label">Business</span>
    <a class="nav-link" href="#invoices">Invoices</a>
    <a class="nav-link" href="#items">Support Items</a>
    <span class="section-label">Coordination</span>
    <a class="nav-link" href="#coordinators">Support Coordinators</a>
    <a class="nav-link" href="#coordination-logs">Coordination Logs</a>
    <a class="nav-link" href="#sc-invoices">SC Invoices</a>
    <span class="section-label">System</span>
    <a class="nav-link" href="#audit">Audit Logs</a>
  </nav>
  <footer class="drawer-footer"><span>admin</span><button type="button">Logout</button></footer>
</aside>
```

- [x] **Step 2: Match the Admin visual language and stable mobile dimensions**

Use the existing neutral Admin palette and a drawer width that remains usable on narrow screens:

```css
:root {
  --brand: #0f766e;
  --brand-soft: #e7f5f3;
  --ink: #18181b;
  --muted: #667085;
  --line: #dfe3e8;
  --drawer-width: min(84vw, 320px);
}

.mobile-drawer {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--drawer-width);
  transform: translate3d(-100%, 0, 0);
  will-change: transform;
  z-index: 30;
}

.nav-link { min-height: 44px; }
.nav-link.active {
  color: var(--brand);
  background: var(--brand-soft);
  box-shadow: inset 3px 0 0 var(--brand);
}

@media (prefers-reduced-motion: reduce) {
  .mobile-drawer, .drawer-backdrop { transition-duration: 0.01ms; }
}
```

- [x] **Step 3: Implement one drawer controller for button and gesture input**

Keep gesture constants conservative and use the same state transitions for every opening method:

```js
const EDGE_ZONE = 24;
const INTENT_DISTANCE = 10;
const OPEN_RATIO = 0.35;
const FLICK_VELOCITY = 0.45;

const state = {
  open: false,
  tracking: false,
  dragging: false,
  pointerId: null,
  startX: 0,
  startY: 0,
  lastX: 0,
  lastTime: 0,
  velocityX: 0,
};

function shouldStartOpening(event) {
  return !state.open && event.isPrimary && event.clientX <= EDGE_ZONE;
}

function resolveIntent(dx, dy) {
  if (Math.abs(dy) > INTENT_DISTANCE && Math.abs(dy) > Math.abs(dx)) return "vertical";
  if (Math.abs(dx) > INTENT_DISTANCE && Math.abs(dx) > Math.abs(dy)) return "horizontal";
  return "pending";
}

function settleDrawer(progress, velocityX) {
  const shouldOpen = progress >= OPEN_RATIO || velocityX >= FLICK_VELOCITY;
  setDrawerOpen(shouldOpen);
}
```

Pointer handling must cancel on vertical intent, `pointercancel`, non-primary input, or a second pointer. Pointer capture begins only after horizontal intent is confirmed. Opening and closing update `aria-expanded`, `hidden`, focus, backdrop state, and body scroll lock.

- [x] **Step 4: Make preview navigation demonstrable without real navigation**

Selecting a drawer item changes only the preview heading and active state, then closes the drawer:

```js
navLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    navLinks.forEach((item) => item.classList.toggle("active", item === link));
    pageTitle.textContent = link.textContent.trim();
    setDrawerOpen(false);
  });
});
```

- [x] **Step 5: Run static source checks**

Run:

```powershell
git diff --check
Select-String -Path 'docs/prototypes/admin-mobile-navigation-demo.html' -Pattern 'EDGE_ZONE = 24','OPEN_RATIO = 0.35','prefers-reduced-motion','aria-expanded'
```

Expected: `git diff --check` has no output; all four required safety/accessibility markers are present.

- [x] **Step 6: Commit the preview**

```powershell
git add -- 'docs/prototypes/admin-mobile-navigation-demo.html'
git commit -m "docs: preview admin mobile navigation"
```

### Task 2: Verify visual layout and primary interactions

**Files:**
- Test: `docs/prototypes/admin-mobile-navigation-demo.html`

- [ ] **Step 1: Open the standalone preview in the in-app browser**

Verification note: the Codex in-app browser blocks direct `file://` navigation by policy. The preview remains a standalone local file and requires user-side opening for visual and touch verification.

Open the file URL for `docs/prototypes/admin-mobile-navigation-demo.html` at a mobile-sized viewport.

Expected: the dashboard loads without a server, the header and hamburger are visible, and the drawer is initially closed.

- [ ] **Step 2: Verify explicit controls**

Test hamburger open, close button, backdrop close, Escape close, and selecting a navigation item.

Expected: every control opens or closes the same drawer; the selected item becomes active and updates the page heading.

- [ ] **Step 3: Verify safe gesture behavior**

Test a left-edge rightward drag, an incomplete drag, an open-drawer leftward drag, a vertical drag near the edge, and a horizontal drag starting away from the edge.

Expected: valid horizontal edge gestures operate the drawer; incomplete gestures return closed; vertical scrolling and non-edge horizontal movement do not open it.

- [ ] **Step 4: Inspect mobile and tablet layouts**

Inspect at approximately 390px, 430px, and 760px widths.

Expected: no clipped labels, overlapping header controls, blank drawer area, or horizontal page overflow. Touch targets remain at least 44px tall.

- [ ] **Step 5: Record verification and final repository state**

Run:

```powershell
git status --short --branch
git log -2 --oneline
```

Expected: the branch contains the design-spec commit and preview commit, with no unrelated modified files.

### Task 3: Integrate the approved navigation into the Admin shell

**Files:**
- Create: `templates/core/partials/admin_navigation_links.html`
- Create: `static/js/admin_nav.js`
- Modify: `templates/admin_base.html`
- Modify: `static/css/admin.css`
- Modify: `core/tests_admin_appearance.py`
- Modify: `core/tests_theme.py`

- [x] **Step 1: Add failing shell and asset tests**

Assert that rendered Admin pages include the mobile menu button, drawer, shared navigation partial output, backdrop, edge zone, and `admin_nav.js`. Assert that Admin CSS and JavaScript contain the mobile hooks and conservative gesture constants.

- [x] **Step 2: Run focused tests and confirm the new assertions fail**

Run:

```powershell
python manage.py test core.tests_admin_appearance core.tests_theme -v 2
```

Expected: failures report missing Admin mobile navigation markup or assets.

- [x] **Step 3: Extract shared navigation links and add mobile shell markup**

Move the existing section labels, links, URL destinations, and active-state conditions unchanged into `templates/core/partials/admin_navigation_links.html`. Include that partial from both the existing desktop navigation and the new mobile drawer.

- [x] **Step 4: Add Admin-only responsive styling**

Add mobile header, drawer, backdrop, active link, footer, edge zone, safe-area, and reduced-motion rules to `static/css/admin.css`. Display them only at `max-width: 760px`; leave desktop behavior unchanged.

- [x] **Step 5: Add the shared button and edge-swipe controller**

Create `static/js/admin_nav.js` with the approved `24px` edge zone, horizontal-intent check, `35%` open threshold, pointer cancellation, body scroll lock, accessibility state updates, focus handling, and resize cleanup.

- [x] **Step 6: Run focused tests and Django checks**

Run:

```powershell
python manage.py test core.tests_admin_appearance core.tests_theme -v 2
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

Expected: tests pass, Django reports no issues, no migrations are generated, and the diff check is clean.

- [x] **Step 7: Push and open a staging PR**

Push `codex/admin-mobile-nav-preview` and create a PR with base `staging`, explicitly noting that production is unchanged until staging validation and a later staging-to-main merge.

Completed in [PR #267](https://github.com/BeezMonkey/BSC_admin/pull/267), targeting `staging`.
