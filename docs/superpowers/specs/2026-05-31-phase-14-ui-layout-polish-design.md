# Phase 14 UI Layout Polish Design

Phase 14 is a low-risk UI and usability pass for the local V1 system. It improves clarity, spacing, navigation, and visual consistency without changing the core business workflows that have already been built and tested.

## Goals

- Improve admin navigation readability and spacing.
- Make dashboard cards feel like usable module entry points.
- Improve table, form, and page header readability across existing pages.
- Make the worker layout easier to use on desktop and mobile.
- Keep the visual style simple enough to replace later with a purchased template if needed.

## Non-goals

- No model changes.
- No database migrations.
- No permission rule changes.
- No workflow or business logic changes.
- No purchased template integration.
- No new JavaScript framework.
- No full redesign of every page.

## Scope

The implementation should stay mostly inside:

- `static/css/app.css`
- `templates/admin_base.html`
- `templates/worker_base.html`
- Existing dashboard and list/detail/form templates only if small structural cleanup is needed for styling.

If a change requires editing models, forms, permissions, or core workflow views, it is out of scope for this phase unless separately approved.

## Admin UI Direction

The admin side should feel more like an internal operations tool:

- Quiet, readable, and work-focused.
- Clear left navigation with enough spacing for scanning.
- Consistent page header and action area.
- Cards used for repeated module entries, not decorative page sections.
- Tables should remain dense enough for operations but easier to read.

## Worker UI Direction

The worker side should stay simple and mobile-friendly:

- Top header remains minimal.
- Bottom navigation remains available.
- Dashboard cards provide clear links to shifts, logs, documents, and profile.
- Spacing should reduce the large empty feel while keeping touch targets comfortable.

## Testing

- Run `python manage.py check`.
- Run relevant template/dashboard tests.
- Run the full app test suite if changes touch shared base templates.
- Browser-check admin dashboard and worker dashboard locally.

## Acceptance Criteria

- UI changes are limited to presentation and low-risk template structure.
- Existing URLs and permissions continue to work.
- Admin and worker dashboards render without template errors.
- Key navigation links remain visible and usable.
- No core business behavior changes are introduced.
