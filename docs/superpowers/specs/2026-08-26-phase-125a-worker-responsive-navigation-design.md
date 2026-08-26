# Phase 125A Worker Responsive Navigation Design

## Goal

Improve the Support Worker portal navigation across desktop, medium-width, and phone-sized screens without changing worker business workflows.

This phase is limited to the worker navigation shell and lightweight responsive layout hooks. It must preserve existing URLs, permissions, forms, shift confirmation, service log submission, document access, and profile pages.

## Visual Direction

The mobile reference provided by the user is used only for the navigation interaction idea:

- a compact menu entry in the top-left area
- a drawer-style navigation surface when opened
- clearer access to worker pages on small screens

The implementation must not copy the reference application's overall visual style. It must continue using the current BSC light admin visual language: pale background, white cards, teal primary actions, subtle borders, and restrained typography.

## Responsive Navigation Rules

### Desktop

Desktop keeps the existing worker sidebar pattern. The worker portal should still feel related to the admin interface on larger screens.

### Medium Window

Medium-width windows should avoid horizontal scrolling navigation. The recommended first implementation is a compact, stable worker navigation layout that keeps all worker destinations reachable without hiding links off-screen.

Acceptable medium behavior:

- wrap navigation into a compact non-scrolling layout, or
- use a compact side/rail layout if it can be implemented safely without disturbing content.

For the first version, prefer the smallest template/CSS change that removes the awkward horizontal nav scroll while keeping content stable.

### Phone

Phone-sized screens should use a top-left menu trigger and a simple drawer menu.

The drawer should contain:

- Dashboard
- My Shifts
- My Logs
- Documents
- Profile
- Logout

The drawer should be simple and BSC-styled. It should not include copied reference details such as profile avatar blocks, app version text, bottom blue navigation, or new product sections.

## Content Boundaries

The following should be preserved from the current worker portal:

- Worker Dashboard content structure
- Shift action summary
- My Shifts card/list direction
- My Logs, Documents, and Profile page content
- Existing page headings and action labels unless a label is required for accessibility

This phase should not redesign the worker content area into the reference mobile app style.

## Accessibility And Interaction

The phone menu should be keyboard and screen-reader friendly:

- menu trigger has a clear accessible name
- drawer has a navigation label
- menu can be closed by a visible close control
- existing links remain normal links
- logout remains a POST form with CSRF protection

JavaScript can be used as progressive enhancement for opening and closing the drawer. If JavaScript fails, the main worker pages should still remain usable through visible navigation at an appropriate fallback breakpoint.

## Testing Scope

Add or update lightweight UI contract tests for:

- worker base includes mobile menu trigger/drawer hooks
- worker navigation links still point to the existing worker URLs
- worker logout remains a POST form
- worker dashboard still renders existing summary and cards
- CSS contains responsive worker navigation rules

Manual frontend checks:

- desktop worker dashboard keeps sidebar behavior
- medium-width window has no body-level horizontal overflow caused by navigation
- phone-width view exposes navigation through the menu
- Dashboard, My Shifts, My Logs, Documents, and Profile remain reachable
- worker shift confirm and complete log paths are not affected

## Out Of Scope

- Admin UI changes
- New worker features
- Bottom mobile navigation
- Copying the provided reference app's full visual style
- Model, URL, permission, or business workflow changes
- Reworking the service log form layout beyond accidental responsive fixes needed for the shell
