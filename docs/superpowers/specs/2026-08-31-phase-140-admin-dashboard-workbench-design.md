# Phase 140: Admin Dashboard Workbench

## Goal

Make the admin dashboard feel like the daily operations home for Brisbane Star Care. The page should answer the admin's first question after login: what needs attention now?

This phase keeps the existing V1 workflow intact and improves the dashboard hierarchy around the current working data: roster shifts, submitted service logs, approved logs ready for invoice, draft invoices, issued invoices, participants, and workers.

## Product Direction

Use a Compact Workbench dashboard: important information first, common actions close at hand, and no unnecessary widget clutter. The visual comparison explored several options; the final direction keeps option A's clarity and borrows only the useful rhythm from option B. Vertex360 is a helpful reference for mature dashboard structure, but BSC Admin should stay simpler and more task-focused.

The page should stay calm, light, and operational:

- Prioritize actionable work over decorative metrics.
- Keep counts linked to the list pages where work continues.
- Keep the six-step workflow visible for orientation and training.
- Preserve the existing module entry points, but make them secondary to the work queue.
- Add recent activity only if it fits without making the first screen feel crowded.

## In Scope

### Header

Rename the dashboard heading toward a workbench tone, such as `Today at BSC` or `Admin Workbench`, with a short subtitle that explains the page as the place to review today's admin follow-up work.

### Operations Overview

Add a compact KPI strip above the main dashboard content. Use available model data only:

- Active participants.
- Active support workers.
- Submitted service logs.
- Approved service logs ready for invoice.

These are informational counts. They should not replace the action queue.

### Priority Queue

Replace or restyle the current `Operations summary` into a more explicit priority queue. Rows should be ordered by operational urgency:

1. Submitted service logs to review.
2. Approved logs ready for invoice.
3. Draft roster shifts to publish.
4. Draft invoices to check or issue.
5. Issued invoices to follow up.

Each row should include:

- Count label.
- Plain-English action.
- Short consequence or context.
- Link to the filtered destination page.

When there is no work in the queue, keep the existing calm zero state concept: no outstanding admin actions.

### Workflow Checklist

Keep the existing six-step workflow checklist:

1. Add participant.
2. Assign worker.
3. Create roster shift.
4. Worker submits service log.
5. Approve service log.
6. Create invoice.

Make it visually secondary to the priority queue. It should remain useful for onboarding and process orientation, but it should not compete with the action queue.

### Module Entry Points

Keep links to the V1 modules:

- Participants.
- Support Workers.
- Roster.
- Service Logs.
- Invoices.
- Documents.
- Support Items.
- Audit Logs.

Restyle them as compact secondary module links or cards below the main dashboard areas. The dashboard should still be usable as a navigation hub, but not only as a navigation hub.

### Recent Activity

Add a small, lower-priority recent activity panel if the existing `AuditLog` data can support it cleanly. Show the latest few audit records with concise action text and a link to the audit log area.

If there are no audit records, show a quiet empty state. This panel should sit below the priority queue, overview, and common module actions. It can be omitted from the first implementation if it makes the page feel too full.

## Out Of Scope

- New reporting charts.
- Compliance panels.
- News feeds.
- Calendar widgets.
- Support worker dashboard changes.
- Permission, role, model, or database schema changes.
- Changing existing URL names or POST workflows.

## Architecture

Keep the implementation in the existing dashboard surface:

- View: `core.views.admin_dashboard`.
- Template: `templates/core/admin_dashboard.html`.
- Styles: `static/css/app.css`.
- Tests: `core/tests_dashboards.py` and focused theme selector assertions if needed.

The view should prepare simple structured context dictionaries/lists for:

- KPI overview counts.
- Priority queue rows.
- Workflow checklist rows.
- Module links.
- Optional recent activity rows from existing audit records.

The template should stay mostly declarative and avoid duplicating business logic.

## Data Flow

Use existing query patterns:

- `Participant.objects.filter(status=Participant.Status.ACTIVE).count()`.
- Active support workers should use existing worker/profile status conventions.
- Submitted logs use `ServiceLog.Status.SUBMITTED`.
- Ready-to-invoice logs use approved logs with no invoice lines.
- Draft and issued invoices use existing invoice statuses.
- Draft shifts use `Shift.Status.DRAFT`.

Counts should be generated server-side and rendered as links to existing list/filter pages.

Recent activity, if included, should use existing `AuditLog` records only. Do not add new tracking behavior in this phase.

## Error And Empty States

If all priority queue counts are zero, show one calm zero state instead of five zero-count rows.

If a supporting count is zero in the operations overview, show `0` normally because overview counts are informational.

All links should still work even when a count is zero, but zero-count priority rows should usually be hidden to reduce noise.

## Testing

Add or update focused dashboard tests to verify:

- KPI overview labels and counts render.
- Priority queue rows render in the expected order when data exists.
- Priority queue rows link to the correct filtered pages.
- Zero state hides zero-count action rows.
- Workflow checklist remains present with current links.
- Module links remain present.
- If recent activity is included, it renders existing audit rows or a quiet empty state.
- Existing role access and sidebar active-state tests continue to pass.

Manual QA should include:

- Desktop dashboard pass.
- Narrow viewport pass around 375px.
- Check that the page still reads as a calm operational admin tool.
