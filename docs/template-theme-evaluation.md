# Template And Theme Evaluation

This document evaluates future UI template/theme options for the Brisbane Star Care NDIS admin system.

Phase 24 does not install, purchase, or integrate a template. It records the selection criteria and a safe future migration path.

## Current UI Status

The project currently uses:

- Django templates.
- A shared admin shell in `templates/admin_base.html`.
- A shared worker shell in `templates/worker_base.html`.
- Plain CSS in `static/css/app.css`.
- Server-rendered pages with no heavy frontend framework.

This is a good base for an internal operations system. It is simple, fast, and easy to adjust. The main limitation is that a custom CSS system requires ongoing design polish if the product grows.

## Product UI Needs

The chosen UI direction should support:

- Dense admin navigation.
- List pages with filters and action buttons.
- Data tables with status badges.
- Detail pages with grouped information.
- Long forms for participants, workers, shifts, support items, invoices, and documents.
- Worker-facing pages that remain simple and clear.
- Mobile usability for workers.
- Accessibility-friendly color contrast and focus states.
- Low maintenance for a small team.

The UI should feel practical and calm, not like a marketing landing page.

## Option 1: Continue Custom CSS

This means continuing with `static/css/app.css` and improving the design incrementally.

### Pros

- Lowest technical risk.
- No new dependency or build system.
- Easy to understand and change.
- Fits current Django template structure.
- Good for ongoing business-flow changes.

### Cons

- More manual design decisions.
- More polish work over time.
- Fewer ready-made components.

### Best For

The next few phases, while fields, workflows, and user feedback are still changing.

## Option 2: Adopt A Bootstrap 5 Admin Template Gradually

Common open-source examples include AdminLTE and Tabler. Both are Bootstrap-based admin UI systems with dashboard, table, form, card, and navigation examples.

### Pros

- Familiar admin layout patterns.
- Ready-made table, form, card, badge, and navigation styles.
- Easier to create a polished business UI.
- Bootstrap-style markup maps reasonably well to Django templates.

### Cons

- Requires adapting many templates.
- May introduce extra CSS and JavaScript.
- Some template examples include components the system does not need.
- Risk of changing visual structure faster than business workflows are ready.

### Best For

A future theme integration phase after core data fields and workflow feedback are stable.

## Option 3: Purchase A Premium Admin Template Later

Premium templates can provide more finished pages, icons, layouts, and support.

### Pros

- More polished out of the box.
- More components and example pages.
- Potentially better documentation and support.

### Cons

- License must be reviewed before use.
- More likely to include a build pipeline or frontend framework.
- Can be expensive to adapt if the app structure is still changing.
- Paid design does not automatically fit NDIS workflows.

### Best For

Later, after the team knows exactly which pages and workflows are stable and worth polishing.

## Candidate Direction

Recommended direction for now:

1. Continue custom CSS for short-term polish.
2. Use Bootstrap 5 style conventions as a future-friendly reference.
3. Evaluate Tabler or AdminLTE as possible future source templates.
4. Avoid premium template purchase until the V1 workflow is accepted by real users.

This keeps the system stable while leaving a clean path toward a more polished admin theme.

## Template Selection Criteria

Any future template should meet these requirements:

- Permissive license for business use.
- Bootstrap 5 or plain HTML/CSS first.
- Minimal required JavaScript.
- No mandatory React/Vue/Angular rewrite.
- Good table and form examples.
- Clear sidebar and topbar layout.
- Responsive behavior that can support worker pages.
- Easy theming for Brisbane Star Care colors.
- No forced dark, gradient-heavy, or decorative visual style.
- Components can be copied into Django templates page by page.

Avoid templates that require:

- A full SPA rewrite.
- Heavy build tooling before any page can render.
- Complex JavaScript interactions for basic forms.
- Marketing-style dashboard layouts that reduce table/form usability.
- Unclear or restrictive licensing.

## Safe Future Migration Path

If the project adopts a template later, use this order:

1. Create a separate theme evaluation branch.
2. Add template assets in a contained static folder.
3. Rebuild only the shared admin shell first.
4. Rebuild one low-risk list page, such as Support Items.
5. Rebuild table, button, badge, and form patterns.
6. Apply the pattern to Participants and Workers.
7. Apply the pattern to Roster, Service Logs, Invoices, and Documents.
8. Review worker pages separately for mobile use.
9. Run browser QA after each group.
10. Keep rollback easy by avoiding unrelated functional changes.

## Pages Most Affected By A Theme

- `templates/admin_base.html`
- `templates/worker_base.html`
- `templates/core/admin_dashboard.html`
- `templates/core/worker_dashboard.html`
- List pages for participants, workers, roster, service logs, invoices, documents, support items, and audit logs.
- Form pages for participants, workers, shifts, recurring shifts, support items, invoices, assignments, and documents.
- Detail pages for all major modules.

## Recommendation

Do not start full template integration yet. The better next step is to continue functional feedback and targeted UI polish. Begin full theme integration only after the business decides that the current page set and workflow structure are stable enough to preserve.

## References

- AdminLTE: https://adminlte.io/
- Tabler: https://tabler.io/
