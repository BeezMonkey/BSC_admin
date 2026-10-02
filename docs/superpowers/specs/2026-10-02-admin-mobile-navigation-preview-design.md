# Admin Mobile Navigation Preview Design

## Goal

Create a standalone HTML preview for the Admin mobile navigation. The preview must demonstrate both an explicit hamburger-menu control and an optional ChatGPT-style edge swipe without changing production templates, URLs, permissions, data, or business logic.

## Navigation Pattern

- Keep the desktop Admin sidebar unchanged.
- On mobile, show a compact top bar with a hamburger button and `BSC Admin` identity.
- Open a left-side drawer containing the existing Admin navigation groups and links.
- Preserve the existing order, section labels, and active-page styling.
- Put the signed-in user and Logout action at the bottom of the drawer.

## Supported Interactions

- The hamburger button opens the drawer.
- A horizontal gesture that starts within 24px of the left viewport edge may open the drawer.
- During a valid edge gesture, the drawer follows the pointer position.
- Release at or above 35% of the drawer width, or with a deliberate rightward flick, opens the drawer; otherwise it returns closed.
- A leftward drag on the open drawer may close it.
- The close button, backdrop click, and Escape key also close it.
- Drawer state is not persisted between page loads.

## Safety Rules

- A swipe that does not begin at the left edge cannot open the drawer.
- Vertical movement that exceeds horizontal intent cancels the gesture, preserving normal page scrolling.
- Ignore non-primary pointers and additional simultaneous touches.
- Do not intercept clicks, form controls, links, tables, calendars, or ordinary horizontal scrolling away from the edge.
- Use Pointer Events with pointer capture only after horizontal intent is established.
- Respect `prefers-reduced-motion` by reducing transition movement.
- Lock page scrolling only while the drawer is fully open or actively dragged.

## Visual Treatment

- Drawer width: `min(84vw, 320px)`.
- Use the existing Admin palette, typography, spacing, and restrained border radius.
- Add a neutral backdrop and a clear close icon.
- Maintain touch targets of at least 44px.
- Show the current navigation item with the existing teal accent treatment.

## Preview Scope

- Add one self-contained file under `docs/prototypes/`.
- Include realistic Admin dashboard content only to demonstrate scrolling and gesture behavior.
- Links may update the active visual state but must not navigate to production pages.
- No Django templates, production CSS, JavaScript, models, routes, migrations, or tests are changed in this preview step.

## Verification

- Verify hamburger open and close.
- Verify edge swipe open, incomplete swipe return, and swipe-to-close.
- Verify vertical scrolling near the edge does not open the drawer.
- Verify backdrop, close button, navigation selection, and Escape behavior.
- Inspect at narrow mobile and tablet-sized viewports for clipping and overlap.
