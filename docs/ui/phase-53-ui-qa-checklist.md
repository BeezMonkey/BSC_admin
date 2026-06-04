# Phase 53 UI QA Checklist

This checklist is for manually reviewing the V1 interface after the Phase 52A-52F visual polish work.

Latest findings log: `docs/ui/phase-54b-ui-qa-findings.md`

## Purpose
Use this checklist before starting the next UI polish phase. The goal is to find visible usability issues, group them by priority, and avoid making scattered style changes without a clear reason.

## Test Accounts
- Admin: `admin / BscTest123!`
- Worker: use the current demo worker account available in the local database, such as `worker / BscTest123!` or another seeded worker user.

## Common Review Criteria
For every page, check:

- Page title, subtitle, and primary action are clear.
- Sidebar active state matches the current module.
- Topbar and logout area do not overlap content.
- System messages appear after save or action flows.
- Form labels, fields, checkboxes, errors, and buttons align from the top.
- Tables are readable, with consistent row spacing and action links.
- Status pills are visible, compact, and semantically colored.
- Empty states are clear and include the expected next action.
- Pagination is readable and preserves filters.
- Buttons have consistent size and weight.
- Text does not overflow or overlap at the current browser width.

## Admin Pages

### Dashboard
URL: `/admin-dashboard/`

- Operations summary cards scan clearly.
- Zero state reads naturally when there are no outstanding items.
- Module cards have consistent spacing and button placement.
- Sidebar active state highlights Dashboard.

### Participants
URLs:
- `/participants/`
- `/participants/new/`
- `/participants/<id>/`
- `/participants/<id>/edit/`
- `/participants/<id>/assign-worker/`

Check:
- Filters, Search, Reset, Add Participant align consistently.
- Empty and filtered-empty states are clear.
- View/Edit buttons align in table rows.
- Detail readiness panels and next-step actions are easy to scan.
- Add/Edit form sections align fields from the top, especially when validation errors appear.
- Assign Worker checkbox, date fields, and notes align cleanly.

### Support Workers
URLs:
- `/workers/`
- `/workers/new/`
- `/workers/<id>/`
- `/workers/<id>/edit/`

Check:
- Worker filters and table actions align consistently.
- Add/Edit Worker form sections remain readable with validation errors.
- Phone field stays aligned with First name and Last name.
- Account active checkbox appears compact and intentional.
- Compliance fields and status pills are easy to scan.

### Roster
URLs:
- `/roster/`
- `/roster/new/`
- `/roster/recurring/new/`
- `/roster/<id>/`
- `/roster/<id>/edit/`

Check:
- Date, participant, worker, and status filters do not wrap awkwardly.
- New Shift and Create Recurring Shifts buttons are easy to distinguish.
- Shift rows show date, time, participant, worker, service, status, and actions clearly.
- Shift detail workflow panel is understandable.
- Create/Edit shift forms align date/time fields and validation errors.

### Service Logs
URLs:
- `/service-logs/`
- `/service-logs/<id>/`

Check:
- Status filter, Clear button, and bulk invoice action align cleanly.
- Approved log checkbox column is understandable.
- Create Invoice action is visible for approved logs only.
- Empty state guides the user back to Roster.
- Detail review actions are visually clear.

### Invoices
URLs:
- `/invoices/`
- `/invoices/new/`
- `/invoices/<id>/`

Check:
- Invoice filters by number, participant, status, and date range are readable.
- Create Invoice form preview controls align.
- Invoice totals show two decimals.
- Draft delete action is visible but not visually dominant.
- Detail status actions and export links are clear.

### Documents
URLs:
- `/documents/`
- `/documents/new/`
- `/documents/<id>/`

Check:
- Upload Document button is obvious.
- Empty state explains what documents are for.
- Detail/download actions are easy to find.
- Linked record text remains readable.

### Support Items
URLs:
- `/settings/support-items/`
- `/settings/support-items/new/`
- `/settings/support-items/<id>/`
- `/settings/support-items/<id>/edit/`

Check:
- Support item filters align.
- Long support item names remain readable in tables.
- Price, GST, status, and action columns scan clearly.
- Create/Edit forms preserve compact field alignment.

### Audit Logs
URLs:
- `/audit-logs/`
- `/audit-logs/<id>/`

Check:
- Audit table is readable.
- Empty state is not visually overbearing.
- Detail page makes actor, action, object, and summary easy to scan.

## Worker Pages

### Worker Dashboard
URL: `/sw/dashboard/`

Check:
- Summary cards make next actions obvious.
- Sidebar or compact nav is easy to use.
- No shift action zero state is quiet and clear.

### My Shifts
URLs:
- `/sw/shifts/`
- `/sw/shifts/<id>/`

Check:
- Needs attention, upcoming, and completed states are visually distinct.
- View and action buttons are easy to tap.
- Completed/history shifts are lower visual priority.
- Shift detail confirm/log actions are clear.

### My Logs
URLs:
- `/sw/logs/`
- `/sw/logs/new/<shift_id>/`
- `/sw/logs/<id>/`

Check:
- Empty state explains when logs appear.
- Service log form fields are easy to complete.
- Submitted/approved/rejected states are visible.
- Rejection reason is readable when present.

### Worker Documents
URLs:
- `/sw/documents/`
- `/sw/documents/<id>/`

Check:
- Document list is clear on narrow widths.
- Download/detail actions are obvious.

### Worker Profile
URL: `/sw/profile/`

Check:
- Profile details are readable.
- Sidebar/nav does not feel awkward during worker use.

## Issue Log Template
Use this format while testing:

```text
Priority: P1 / P2 / P3
Page:
URL:
Role: Admin / Worker
Issue:
Screenshot:
Suggested fix:
```

## Next-Phase Decision Rules
- If any P1 issues are found, fix them before adding new features.
- If multiple P2 issues affect the same component, create a focused polish phase for that component.
- If only P3 issues remain, continue with the next functional or deployment phase.
- If worker mobile use feels weak, prioritize a worker-facing responsive polish phase.
- If admin tables feel cramped with larger data, prioritize dense table and filter usability.

## Current Recommended Next Areas
After this QA pass, likely candidates are:

- Worker mobile/narrow-width refinement
- Invoice PDF branding and layout
- Admin table density for larger participant/worker lists
- Dashboard operational metrics refinement
