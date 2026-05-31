# Phase 16 Worker Shell Polish Design

Phase 16 tests a more scalable worker layout. It changes the worker navigation from a fixed bottom bar to an admin-like app shell while keeping the worker experience lighter than the admin side.

## Goals

- Make worker navigation easier to use on desktop browsers.
- Align worker pages with the admin system layout language.
- Keep worker navigation simple and role-specific.
- Remove the fixed bottom navigation bar.
- Keep mobile navigation usable without adding JavaScript.

## Non-goals

- No business workflow changes.
- No URL changes.
- No permission changes.
- No model or database changes.
- No complex hamburger menu.

## Layout

- Desktop: left worker sidebar with Dashboard, My Shifts, My Logs, Documents, and Profile.
- Content area: right-side page content with a compact topbar containing username and logout.
- Mobile: sidebar becomes a horizontal top navigation strip above content.

## Acceptance Criteria

- Worker pages render with the new app shell.
- Existing worker links continue to use the same URL names.
- Admin layout is unchanged.
- Existing tests continue to pass.
