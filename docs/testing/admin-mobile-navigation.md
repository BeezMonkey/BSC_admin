# Admin mobile navigation verification

The mobile menu uses the existing overlay drawer. Open it with the hamburger
button and close it with the close button, dimmed backdrop, or Escape. The page
stays stationary. Custom swipe and drag handling has been removed for the web
release, leaving touch interactions and browser history gestures to the browser.

Mobile page content has 20 CSS pixels of space below the header. Desktop layout,
drawer appearance, focus trapping, and reduced-motion support are unchanged.

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

The regression uses browser-dispatched touch input rather than synthetic DOM
pointer events. It checks that swipes and mouse drags do not open or close the
menu, while buttons, link cards, form input, vertical and horizontal scrolling,
keyboard focus, menu links, viewport changes, and reduced motion still work.
It also checks header spacing and mobile layout at 320, 390, and 760 CSS pixels.

These checks passed locally along with the 35 focused Django tests. Chromium
mobile emulation is not an iPhone Safari acceptance test.

## Staging acceptance

After merging the PR into staging and waiting for deployment:

1. On iPhone Safari, open the Admin dashboard. Check that the page heading has
   comfortable space below the mobile header.
2. Open the menu with the hamburger button. Check the overlay appearance, then
   close it using the close button and, separately, the backdrop.
3. Swipe horizontally on page text, link cards, and the open drawer. These actions
   must not open or close the menu. Browser Back remains a browser action.
4. Tap dashboard cards and menu links. Scroll the dashboard vertically. In Service
   Logs and Roster, edit filters and horizontally scroll tables. Verify there is
   no lost input or stuck scroll lock after closing the menu.
5. Try the browser's own edge-back gesture and pinch zoom separately.

Only Admin navigation presentation and input handling change. Worker and
coordinator shells, backend operations, permissions, billing, and database
schemas are outside this change.
