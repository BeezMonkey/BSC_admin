# Support Worker Desktop Layout Design

## Goal

Make the Support Worker portal comfortable and consistent on desktop and large screens while preserving all business behavior, the existing My Documents presentation, and every layout at 980px and below.

## Scope

- Apply one desktop layout hook to Dashboard, My Shifts, My Logs, Profile, and their non-document detail and form pages.
- Keep each page within a consistent 1180px workspace and allow it to use the available width instead of shrinking to its content.
- Improve desktop spacing and the My Shifts summary layout without changing links, forms, filters, permissions, data, or view logic.
- Leave all document templates unchanged.
- Place every new visual rule inside `@media (min-width: 981px)` so the current mobile and tablet presentation remains unchanged.

## Approach

Templates receive a presentational `worker-desktop-page` class on their outer sections. Desktop-only rules in `static/css/portal.css` stretch those sections to a shared maximum width, normalize card spacing, and make the shift summary use three equal columns. Existing mobile rules and the document templates continue to use the current selectors and behavior.

## Verification

- Automated tests confirm all non-document worker templates contain the desktop hook.
- Automated tests confirm document templates do not contain the hook.
- A CSS contract test confirms the rules are scoped to `min-width: 981px` and use the agreed 1180px maximum width.
- Existing Dashboard, Shifts, Logs, and Profile tests remain green.
- Desktop and mobile screenshots verify the visual result at representative widths.
