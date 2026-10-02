# Admin mobile navigation verification

The approved interaction restores the overlay drawer used before PR #268. The
page stays stationary, while the drawer follows a horizontal drag. The hamburger
button, close button, dimmed backdrop, and Escape remain available.

Opening gestures start on non-interactive page content, at least 32 CSS pixels
from the left edge. Inputs, links, buttons, dialogs, tables, and other horizontally
scrollable containers keep their native interactions. The gesture is cancelled
when the user starts scrolling vertically or introduces another finger.

## Automated checks

With Django dependencies installed:

```sh
python manage.py test core.tests_admin_appearance core.tests_theme
python manage.py check
```

With Node.js, Playwright, and Chromium installed:

```sh
node --check static/js/admin_nav.js
node scripts/check_admin_mobile_nav.cjs
```

`CHROME_PATH` may point to an existing Chrome executable. `ADMIN_NAV_CAPTURE_DIR`
optionally saves screenshots. The browser check uses an isolated mobile context,
the repository's shell and assets, and an in-memory test page. All network requests
are intercepted; it never accesses staging, production, or a database.

The regression uses browser-dispatched touch input, including browser scroll and
history handling, rather than JavaScript-dispatched pointer events. It fails on
the previous implementation because a rightward touch navigates back. It checks
opening and closing, central-content swipes, short drags, vertical scrolling,
form and horizontal-scroll exclusions, touch cancellation, multi-touch,
keyboard focus, menu links, viewport changes, and reduced motion.

These checks passed locally along with the 35 focused Django tests. Chromium
mobile emulation is not an iPhone Safari acceptance test.

## Staging acceptance

After merging the PR into staging and waiting for deployment:

1. On iPhone Safari, open the Admin dashboard and swipe right from its heading or
   another non-interactive content area, away from the physical screen edge.
2. Check that the drawer follows the finger, settles open, and retains the earlier
   overlay appearance. A short slow drag should settle closed.
3. Try the hamburger, close button, backdrop, and a leftward swipe from the drawer
   header. Follow a menu link and use browser Back.
4. Scroll the dashboard vertically. In Service Logs and Roster, interact with
   filters and horizontally scroll tables. Verify there is no accidental menu
   opening, lost form input, or stuck scroll lock.
5. Try the browser's own edge-back gesture and pinch zoom separately.

Only Admin navigation presentation and input handling change. Worker and
coordinator shells, backend operations, permissions, billing, and database
schemas are outside this change.
