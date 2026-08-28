# BSC UI Design System v1

Last updated: 2026-08-28

This document defines the working UI rules for BSC Admin. It is intentionally practical: the goal is to keep future phases consistent, reduce user mistakes, and protect the business workflow that already works.

## Product Direction

BSC Admin has two related but different interfaces:

- Admin interface: a clear back-office system for managing participants, workers, rosters, service logs, invoices, documents, and audit records.
- Worker interface: a simple mobile-friendly tool for support workers to confirm shifts, complete service logs, review documents, and keep profile details current.

The UI should optimize for:

- Clear hierarchy: users know where they are and what matters.
- Low cognitive load: common tasks are obvious.
- Minimum input: the system should reuse known information.
- Immediate feedback: users know whether an action worked.
- Error prevention: destructive and financial actions are harder to do accidentally.
- Workflow-first design: screens support the full NDIS operations loop rather than isolated database records.

## Page Structure

Every admin page should follow this order unless there is a strong workflow reason not to:

```text
Page title
Short description
Primary action
Filters or summary
Main content
Secondary information
Danger zone
```

Rules:

- The page title names the business area, such as `Support Workers`, `Roster`, or `Invoices`.
- The description should explain the page in one short sentence.
- The primary action should be visually easy to find and should normally sit near the top right.
- Filters belong above the main table or list.
- Dangerous actions belong at the bottom of an edit/detail page, not beside everyday fields.

## Button Hierarchy

Use button styles by intent, not decoration.

| Button type | Use for | Placement |
| --- | --- | --- |
| Primary | Main next action, such as `Add Worker`, `Create Invoice`, `Confirm`, `Complete Log` | Page header, form footer, or card action area |
| Secondary | Back, cancel, view, reset, supporting action | Beside or below the relevant primary action |
| Row action | Table actions such as `View` and `Edit` | Right side of the row |
| Danger | Delete, archive, deactivate, cancel invoice, destructive workflow action | Danger zone or confirmed destructive flow |

Rules:

- A page should normally have one dominant primary action.
- Worker mobile cards can have one large primary action plus one smaller secondary action.
- `Delete` is red and always requires confirmation.
- `Deactivate`, `Archive`, and `Login disabled` should not look identical to permanent deletion.
- Avoid placing several same-weight buttons next to each other when one action is clearly more important.

## Tables And Lists

Admin tables are the main work surface. They should show only the fields needed to make decisions on that page.

General table rules:

- Text columns align left.
- Numeric columns, hours, quantities, rates, and amounts align right.
- Status values use compact badges.
- Row actions stay on the right.
- Tables should support search/filter where the list can grow.
- Empty states should explain what happened and what to do next.

Recommended Support Workers list:

```text
Name | Email | Phone | Type | Status | Actions
```

Compliance details should usually live on the worker detail/edit pages or a future compliance-focused surface. The worker list should stay easy to scan.

Recommended Participants list:

```text
Participant | NDIS No. | Phone | Plan Manager | Status | Actions
```

Recommended Invoices list:

```text
Invoice | Participant | Period | Status | Total | Actions
```

Recommended Service Logs list:

```text
Select | Date | Participant | Worker | Status | Hours | Notes | Actions
```

## Forms

Forms should follow business sections rather than database order.

Support Worker form sections:

```text
Personal Details
Contact Details
Employment
Compliance
Login Access
Danger Zone
```

Participant form sections:

```text
Personal Details
NDIS Details
Contact
Plan Manager
Billing / Invoice Defaults
Worker-visible Notes
Internal Notes
Documents
```

Roster form sections:

```text
Participant and Worker
Date and Time
Support Item
Instructions
Publish Status
```

Invoice settings form sections:

```text
Business Details
Logo
Payment Details
Invoice Numbering
PDF Display Defaults
```

Rules:

- Labels should be clear and business-friendly.
- Helper text should explain risk or consequence, not repeat the label.
- Required fields should be obvious.
- Validation messages should explain how to fix the problem.
- Save/cancel placement should be consistent within admin forms.
- Login access and destructive actions should sit near the bottom so they are deliberate.

## Status Language

Status labels should be consistent across screens.

| Area | Status | Meaning |
| --- | --- | --- |
| Worker account | `Login enabled` | Worker can sign in. |
| Worker account | `Login disabled` | Worker record remains, but the user cannot sign in. |
| Worker record | `Active` | Worker can be used in normal operations. |
| Worker record | `Archived` | Worker is retained for history but hidden from active scheduling. |
| Shift | `Draft` | Admin-created but not visible to worker. |
| Shift | `Published` | Visible to worker and awaiting confirmation. |
| Shift | `Confirmed` | Worker has confirmed the shift. |
| Shift | `Completed` | Shift has a completed service log. |
| Service log | `Submitted` | Worker has submitted the log for admin review. |
| Service log | `Approved` | Admin has approved the log for invoice use. |
| Service log | `Invoiced` | Log has been used in an invoice. |
| Invoice | `Draft` | Invoice exists but has not been issued. |
| Invoice | `Issued` | Invoice has been finalized/sent. |

Rules:

- Do not mix `Inactive`, `Disabled`, and `Archived` unless they mean different things.
- Use short badge labels in tables.
- Explain consequences in detail pages or danger-zone copy.

## Feedback And Empty States

Users should never have to guess whether an action worked.

Use clear feedback for:

- Saved changes.
- Submitted service logs.
- Approved/rejected logs.
- Generated invoices.
- Deleted draft invoices.
- Login access changes.
- Archive/deactivate actions.

Empty states should be useful:

```text
No service logs found.
Try changing the filters, or create and publish roster shifts first.
```

Avoid generic states such as:

```text
No data.
Error.
Invalid.
```

## Color Rules

Colors should communicate meaning.

| Color role | Use |
| --- | --- |
| Teal / green | Primary actions and success |
| Yellow | Waiting, pending, needs attention |
| Red | Danger and destructive actions |
| Grey | Neutral text, disabled, secondary context |
| Blue-grey | Supporting information |

Rules:

- Do not introduce new colors for one-off decoration.
- Status colors should stay consistent across admin and worker views.
- Danger actions should be visually separate from everyday actions.

## Typography And Spacing

Use a small, predictable type scale:

| Role | Approximate size |
| --- | --- |
| Page title | 24-32px |
| Section title | 18-22px |
| Body | 14-16px |
| Table text | 14-16px |
| Helper text | 12-14px |

Rules:

- Avoid too many font sizes on one page.
- Do not use large hero-style headings inside compact admin tables or forms.
- Text should not overflow buttons, cards, or form fields.
- Cards should not be nested inside other cards unless there is a clear functional reason.

## Worker Mobile Rules

The worker interface is mobile-first. It should not feel like a compressed admin dashboard.

Worker dashboard:

- Show the most important daily actions first.
- Keep navigation behind a hamburger drawer on phone-sized screens.
- Keep the current worker identity visible but compact.
- Make primary actions easy to tap.

Worker shift cards:

- Show date and time first.
- Show participant name clearly.
- Show status as a badge.
- Place `View` as a secondary action.
- Place `Confirm` or `Complete Log` as the dominant action.
- Avoid horizontal scrolling.

Worker service log form:

- Inputs must stay inside the viewport on iPhone/Safari and Android/Chrome.
- Time inputs must remain usable on narrow screens.
- The worker should only enter actual time, break, kilometres, and notes when needed.
- Admin-controlled invoice amounts should not be exposed to the worker.

## Admin Responsive Rules

Admin is desktop-first but should remain usable on smaller windows.

Rules:

- Medium windows should wrap controls cleanly instead of forcing horizontal overflow.
- Mobile admin views should support urgent review or simple actions, but do not need to become app-style flows.
- Tables may become scrollable only when there is no better compact representation.
- Filter bars should wrap predictably.
- Primary actions must remain reachable.

## Workflow-Specific Rules

### Participant To Invoice Flow

The full workflow should stay understandable:

```text
Participant
Worker
Support Item
Roster Shift
Worker Confirmation
Service Log
Admin Review
Invoice
PDF Export
```

Rules:

- When a user selects a participant, known NDIS and plan manager information should flow through automatically.
- When a user selects a support item, the code, description, unit, and price limit should be reused.
- Worker-entered kilometres should remain a service-log input.
- Admin controls the final travel amount/rate used for invoice calculation.

### Invoice PDF Rules

- PDF output should prioritize clarity for external readers.
- Dates should use Australian format.
- Invoice numbers should use the global sequence.
- Service and travel lines should include meaningful descriptions and support item codes.
- Multi-page invoices must keep headers, continuation labels, line-item flow, and totals stable.

## Design Review Checklist

Before merging UI changes, check:

- Is the page title clear?
- Is there one obvious primary action?
- Are secondary actions visually quieter?
- Are destructive actions separated and confirmed?
- Does the table show only useful columns?
- Are numbers, money, and hours aligned consistently?
- Are statuses short and consistent?
- Does the form follow business sections?
- Does the page have useful empty/error/success states?
- Does the worker mobile view work without horizontal scrolling?
- Does the admin medium-window view wrap cleanly?
- Does the change preserve the existing business workflow?

## Implementation Principle

Do not redesign the whole product in one phase. Apply this design system gradually:

1. Use it for new work by default.
2. Apply it to nearby UI when touching an existing page.
3. Avoid broad restyling unless it fixes a real usability problem.
4. Prefer small, testable phases with clear PR titles.

This document should be updated when BSC makes a deliberate design decision that future work should follow.
