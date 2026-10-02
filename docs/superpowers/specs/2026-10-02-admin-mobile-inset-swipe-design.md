# Admin Mobile Inset Swipe Design

## Goal

Replace the Admin mobile drawer's screen-edge gesture with an inset, content-surface gesture that avoids Safari's back navigation and visually follows the user's finger like the ChatGPT mobile panel.

## Verified Problem

The current controller starts only when `clientX <= 24`. On iPhone Safari, that area belongs to the browser's interactive back gesture, so Safari navigates backward before the page can reliably open the Admin drawer. The current animation also translates the drawer over a stationary page, while the desired interaction keeps the drawer underneath and translates the main page surface.

## Interaction Design

### Closed state

- Keep the hamburger button as the primary, reliable way to open navigation.
- Permit a rightward gesture only when it begins between 32px and 112px from the left edge of the main page surface.
- Leave the first 32px untouched so Safari retains its native back gesture without competing with the application.
- Ignore gesture starts on links, buttons, form controls, editable content, and horizontally scrollable regions.
- Wait for at least 12px of movement before deciding intent. Vertical intent cancels tracking; only clear horizontal intent begins the drawer interaction.
- Once horizontal intent is established, move the complete main surface with the finger while the drawer remains fixed underneath.

### Open state

- Rest the main surface at the drawer width, with a subtle left-edge radius and shadow.
- Keep drawer links, scrolling, close button, user identity, and Logout fully interactive.
- Close through the existing close button, tapping the dimmed main surface, pressing Escape, or swiping the main surface left.
- Return focus to the hamburger button after button- or keyboard-initiated closure. Gesture closure does not force focus.

## Structure

- Add one `.admin-mobile-surface` wrapper around the existing mobile header and Admin content.
- On desktop, use `display: contents` so the existing two-column Admin grid and sidebar remain unchanged.
- On mobile, make the wrapper the translated foreground surface.
- Keep the mobile drawer fixed behind the surface instead of translating the drawer itself.
- Remove the obsolete `.admin-edge-swipe-zone` element and its CSS.
- Reuse the existing shared navigation partial, routes, active states, and logout form without changes.

## Gesture Controller

The controller continues to own one open/closed state for hamburger, keyboard, tap, and gesture input. It will:

- track pointer movement from the main surface rather than a screen-edge element;
- use `INSET_START = 32`, `INSET_END = 112`, `INTENT_DISTANCE = 12`, and the existing conservative settle thresholds;
- set the surface translation and dimming progress during a drag;
- cancel cleanly on vertical intent, `pointercancel`, desktop breakpoint changes, and incomplete drags;
- avoid global `touch-action` rules that could disable horizontal table scrolling.

## Safety And Scope

- No models, views, forms, URLs, permissions, database behavior, or billing logic change.
- Desktop Admin layout remains unchanged above 760px.
- Support Worker and Support Coordinator portals remain unchanged.
- Safari's native back gesture remains available in the first 32px of the viewport.
- Reduced-motion settings continue to shorten transitions.

## Verification

- Add failing template and asset tests before production changes.
- Verify the old edge-zone element is absent and the new mobile surface exists.
- Verify gesture constants, interactive-target exclusions, vertical-intent cancellation, and pointer cancellation are present.
- Run the focused Admin appearance/theme tests, Django checks, migration check, JavaScript syntax check, diff check, and the full Django suite.
- In a mobile browser viewport, test hamburger open, surface-following drag, incomplete drag, vertical scroll, tap-to-close, left-swipe close, Escape, drawer scrolling, and desktop reset.
- Deploy only to `staging` for final iPhone Safari verification before any later staging-to-main merge.
