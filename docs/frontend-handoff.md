# Frontend Handoff

This document gives a frontend designer or engineer the shortest useful path into the Brisbane Star Care admin UI. It focuses on workflow understanding, interaction polish, and safe UI implementation.

For deeper context, read these first:

- `docs/business-workflow-review.md` for the core business loop and known V1 gaps.
- `docs/beta-tester-guide.md` for the real admin, worker, and finance trial paths.
- `docs/ui/phase-53-ui-qa-checklist.md` for manual UI review criteria.
- `docs/superpowers/specs/2026-06-08-phase-84-planner-view-mode-design.md` for the latest Quick Roster Planner direction.

Do not copy beta passwords into shared notes, screenshots, commits, or design files. Ask the project owner for current test credentials when needed.

## Product Shape

Brisbane Star Care is an NDIS admin workflow tool. The current V1 is not a generic dashboard; it is an operations loop from client setup through billing.

Core workflow:

```text
Participant -> Worker -> Assignment -> Roster -> Worker Service Log -> Admin Review -> Invoice -> Export
```

The UI should make this loop feel obvious. Each screen should answer one of these questions:

- What needs my attention now?
- What is the next safe action?
- Is this record ready for the next workflow step?
- What history or audit trail protects this action?

## User Roles

### Admin

Admin users manage the day-to-day workflow:

- Create and maintain participants.
- Create and maintain support workers.
- Assign workers to participants.
- Create, publish, and manage roster shifts.
- Review submitted service logs.
- Create invoices from approved logs.
- Upload documents.
- Review audit logs.

Admin pages can be information-dense, but they must stay scannable.

### Worker

Worker users need a simpler, task-first experience:

- Open My Shifts.
- Confirm published shifts.
- Complete service logs.
- Review submitted logs.
- View shared documents.
- Check profile details.

Worker pages should prioritize the next action over admin-style data density, especially on mobile.

### Finance / Accountant

Finance users care about invoice review and exports:

- Filter invoices.
- Open invoice detail.
- Check period, participant, line items, quantity, unit price, and total.
- Download CSV/PDF.
- Understand invoice status.

## Page Map

### Admin Navigation

Use the real V1 module names in the main admin sidebar:

- Dashboard
- Participants
- Support Workers
- Roster
- Service Logs
- Invoices
- Documents
- Support Items
- Audit Logs

Do not add unavailable modules such as CRM or Forms until the backend routes and workflows exist.

### Admin Pages

`/admin-dashboard/`

- Operations summary.
- Workflow checklist.
- Module entry cards.
- Should become the operational home page, not a generic metric dashboard.

`/participants/`

- Search by name or NDIS number.
- Status filter.
- Sortable table.
- Add Participant.
- View/Edit row actions.

`/participants/<id>/`

- Readiness.
- Next steps.
- Overview.
- NDIS Plan.
- Notes.
- Assigned Workers.
- Related Records placeholder.

`/workers/`

- Search by name, email, or phone.
- Status and employment type filters.
- Sortable table.
- Add Worker.
- View/Edit row actions.

`/roster/`

- Quick Planner.
- New Shift.
- Create Recurring Shifts.
- Quick date filters.
- Date/participant/worker/status filters.
- Shift table with next action.

`/roster/planner/`

- Participant view / Worker view.
- Participant and worker filters.
- Date range.
- Seven-day grid.
- Day-level add shift action.
- Shift cards.

`/service-logs/`

- Status filter.
- Bulk invoice action for approved logs.
- Wide table with select/date/participant/worker/status/hours/notes/actions.
- This page needs a focused responsive strategy before real data volume grows.

`/invoices/`

- Invoice number, participant, status, and period filters.
- Create Invoice.
- Invoice table.
- CSV/PDF export on detail.

`/documents/`

- Upload Document.
- Document table.
- Empty state should explain what documents are for.

`/settings/support-items/`

- Support item search and filters.
- Long item names must wrap cleanly.
- Price/GST/status/actions must scan clearly.

`/audit-logs/`

- Audit table and detail page.
- Actor, action, object, and summary should be easy to scan.

### Worker Pages

`/sw/dashboard/`

- Shift action summary.
- Links to My Shifts, My Logs, Documents, Profile.

`/sw/shifts/`

- Needs attention, upcoming, completed counts.
- View filters.
- Grouped shift list.
- Primary actions should be easy to tap.

`/sw/shifts/<id>/`

- Shift date, time, status, address, instructions, service.
- Confirm Shift when published.
- Complete Service Log when eligible.

`/sw/logs/`

- Submitted/approved/rejected states must be clear.
- Empty state should explain when logs appear.

`/sw/logs/new/<shift_id>/`

- Replace generic `form.as_p` output with the shared field component pattern when polishing this page.

`/sw/documents/`

- Clear list with obvious detail/download actions.

`/sw/profile/`

- Readable worker details.
- No admin-only complexity.

## Interaction Rules To Preserve

Preserve these existing behaviours during visual refactors:

- Sidebar active state must match the current module.
- List filters must preserve query state.
- Reset should clear filters predictably.
- Sortable table headers should keep using safe whitelisted sort fields.
- View/Edit links should carry `next` when returning to filtered lists matters.
- Create/Edit Cancel should return to the originating list or context when possible.
- Pagination should preserve filters.
- Status pills should remain text labels, not color-only indicators.
- Destructive actions must use POST and CSRF protection.
- Draft records can expose delete only where the workflow explicitly allows it.
- Published, confirmed, completed, cancelled, no-show, approved, invoiced, and audited records should preserve history.

## Design Direction

The preferred visual direction is the current Figma single-version admin concept:

- Font: Inter.
- Calm, light admin UI.
- Neutral surface palette with BSC teal as the main accent.
- Low-noise sidebar.
- Subtle tabs and segmented controls.
- Clean tables with compact row actions.
- Status chips with semantic but restrained colors.
- Roster planner that feels like an operational tool, not a decorative calendar.

Reference:

```text
https://www.figma.com/design/33xY8dWTVauCEhqWYG9Qq4/BSC-Admin-UI-Direction?node-id=43-2
```

The frontend should not blindly reproduce the Figma menu labels if they differ from the live V1 modules. Treat Figma as the visual direction and the Django app as the source of truth for routes and behaviours.

## Component Guidance

### Layout

- Keep the admin shell predictable: sidebar, topbar, content area.
- Consider moving the admin sidebar from dark green to the lighter Figma direction, but keep real module names.
- Use consistent page headers: title, subtitle, primary actions.
- Avoid nested cards unless they represent repeated records or a genuinely framed tool.

### Tables

- Keep tables dense but readable.
- Use consistent header weight, row height, border color, and hover state.
- Keep row actions visually compact.
- For wide tables such as Service Logs, use horizontal scroll on desktop and a card/list strategy on narrow screens.
- Use tabular number alignment for money, hours, and dates where practical.

### Filters

- Use one shared filter bar pattern.
- Labels must remain visible.
- Date ranges should align as a pair.
- Quick filters should look like segmented controls or compact pills.
- Reset should be secondary.

### Forms

- Use visible labels, not placeholder-only fields.
- Show field errors next to the relevant field.
- Use consistent section headers.
- Add a sticky or consistently placed action area for long forms.
- Keep Save primary and Cancel secondary.
- Be careful with destructive submit buttons near normal Save actions.

### Status And Warnings

Use a consistent status dictionary:

- Neutral: draft, completed, inactive, archived.
- Teal/green: active, approved, confirmed, paid, ready.
- Amber: published, submitted, pending, needs attention.
- Red: rejected, cancelled, no-show, expired, missing.
- Teal accent: invoiced or workflow-complete states.

Do not rely on color alone. The chip text must carry the meaning.

### Messages

Success and error messages should be visually obvious after critical actions:

- Worker confirms shift.
- Worker submits service log.
- Admin approves/rejects service log.
- Admin creates invoice.
- Admin downloads/export files.
- Admin archives/cancels records.

Messages should stay near the top of content and use `role="status"` / `aria-live` where appropriate.

## High-Value UX Improvements

### 1. Operational Dashboard

Keep the current `Operations summary + Workflow checklist`, but restyle it toward the Figma direction. The dashboard should surface:

- Draft shifts.
- Submitted logs.
- Approved logs ready for invoice.
- Draft invoices.
- Issued invoices.
- The six-step workflow checklist.

This page should be the fastest place for an admin to know what to do next.

### 2. Readiness Panels

Participant and worker detail pages should make readiness impossible to miss:

- Missing NDIS number.
- Missing plan dates.
- Missing active worker assignment.
- Expired or soon-expiring worker compliance.
- Missing support item.
- Inactive participant/worker.

Readiness should include both state and action.

### 3. Quick Roster Planner

The planner should remain familiar and lightweight:

- Keep the seven-day grid.
- Keep Participant view and Worker view.
- Keep day-level `+` add action.
- Show the correct context on each shift card.
- Add per-shift actions inside the card: View, Edit, Copy.
- Only show Delete for Draft shifts.

Do not introduce a complex fortnight timeline yet.

### 4. Worker Mobile Flow

Worker mobile use is high-risk and should get its own QA pass:

- My Shifts should show Needs attention first.
- Confirm Shift and Complete Service Log should be large, clear actions.
- Completed/history shifts should have lower visual priority.
- Service Log form fields should be easy to complete on a phone.

### 5. Service Logs Density

The Service Logs table is already a known wide-table risk. Treat it as a focused component problem:

- Desktop: dense table.
- Tablet: horizontal scroll with sticky first/action column if feasible.
- Mobile: stacked log cards.
- Keep bulk invoice action visible only when relevant.

## Recommended Implementation Order

### Phase A: Design Tokens And Shared UI

- Update color tokens.
- Update typography scale.
- Update button styles.
- Update status pills.
- Update card/table/filter/form/message styles.
- Keep backend routes and templates intact.

### Phase B: Admin High-Frequency Pages

- Dashboard.
- Participants list.
- Participant detail.
- Roster list.
- Quick Roster Planner.
- Service Logs list.

### Phase C: Worker Task Flow

- Worker Dashboard.
- My Shifts.
- Worker Shift Detail.
- Complete Service Log.
- My Logs.

### Phase D: Finance And Support Pages

- Invoices list/detail/create.
- Documents.
- Support Items.
- Audit Logs.

## QA Checklist For UI Work

Before finishing any UI polish phase, check:

- Page title, subtitle, and primary action are clear.
- Sidebar active state is correct.
- Buttons have consistent size, weight, and hover/focus states.
- Tables are readable and actions align.
- Status chips are compact and meaningful.
- Empty states include the next safe action.
- Form labels and errors align.
- Text does not overflow at desktop width.
- Worker pages are usable on narrow/mobile widths.
- No existing workflow action was removed or renamed without product approval.

## Implementation Safety Notes

- UI work should not change permissions.
- UI work should not change field names, form names, or POST destinations unless the backend tests are updated intentionally.
- Do not remove CSRF-protected forms for destructive actions.
- Do not replace real links with fake buttons.
- Do not hide audit-relevant actions.
- Do not create front-end-only states that the backend does not understand.
- Keep accessibility basics: visible focus states, labels, semantic headings, and readable contrast.

## Suggested First Pull Request

Start with a small, low-risk visual foundation PR:

1. Refine CSS tokens in `static/css/app.css`.
2. Restyle the admin sidebar, page header, buttons, tables, filter bars, status pills, and messages.
3. Update Dashboard and Roster Planner only where markup changes are necessary.
4. Run the existing tests and a manual browser pass on admin dashboard, participants list/detail, roster list, planner, and worker shifts.

This creates a clean baseline before touching the longer forms and finance flows.
