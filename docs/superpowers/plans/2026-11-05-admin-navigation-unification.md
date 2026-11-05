# Admin Navigation Unification

**Goal:** Use the approved icon sidebar on all Admin pages without opting their content into the R1 shell.

**Scope:** Sidebar width, brand, navigation typography, spacing, icons and selected/hover/focus appearance. Preserve the shared link partial, route matching, mobile drawer script, permissions, header/account placement and all business content. No deployment, database, storage or role-portal changes.

**Approach:** Load a standalone `admin_navigation.css` from `admin_base.html`, scoped by the existing Admin data attribute. Use the existing SVG assets and approved navigation colors locally, without changing inherited content tokens or loading `r1_shell.css` on old-shell pages. Desktop width becomes 212px; retain the existing 760px mobile breakpoint and 44px drawer targets.

## Verification

- [x] Add failing tests covering all Admin page families, unchanged route order, POST logout, role isolation, stylesheet scope and resource ordering.
- [x] Freeze baseline template/static assets and render fictional before samples.
- [x] Add the navigation-only stylesheet using the existing Admin attribute, without changing shell markup.
- [x] Run focused then full Python and JavaScript regressions; report PostgreSQL skips separately and rerun the isolated PostgreSQL verifier.
- [x] Compare actual computed navigation styles and non-navigation content styles before/after, including desktop/mobile, keyboard drawer operation and overflow checks.
- [x] Preserve old HTML and create a separate local comparison with desktop/mobile switching. Report local status explicitly; do not deploy Main or Staging.

Verified locally: 1408 SQLite passes plus 3 actual PostgreSQL passes, 131 JavaScript passes, 56 page/width combinations and 759 browser assertions. No existing tests modified. Read-only independent review found no actionable issues. Evidence and standalone preview are in `outputs/admin-navigation-unification-20261105` in the main workspace. Deployment and user acceptance are not included.
