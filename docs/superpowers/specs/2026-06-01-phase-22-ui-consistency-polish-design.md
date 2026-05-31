# Phase 22 UI Consistency Polish Design

## Purpose

Phase 22 improves the visual consistency of the existing Django template UI without changing business workflows, permissions, URLs, database models, or page content.

## Scope

- Standardize table container spacing.
- Make list row borders and table edges feel continuous.
- Make `View` and `Edit` actions visually consistent across admin list pages.
- Improve page header and action-row wrapping behavior.
- Keep the existing admin and worker shell layouts.

## Out Of Scope

- Full third-party template integration.
- New navigation structure.
- New icons or JavaScript UI framework.
- Database or permission changes.
- Business workflow changes.
- Major responsive redesign.

## Approach

Use the existing `static/css/app.css` as the single source for this polish. Prefer global class improvements over editing every template individually. Only change templates if a specific page cannot be fixed through existing classes.

## Expected Result

Admin lists should have steadier spacing, actions should look intentional rather than like loose text links, and table lines should avoid the broken or uneven feel seen in previous screenshots.

## Verification

- Run Django system checks.
- Run focused UI smoke inspection in the browser if the local server is available.
- Run the existing tests if template behavior is touched beyond CSS.
