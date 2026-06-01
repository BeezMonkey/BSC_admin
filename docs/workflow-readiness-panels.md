# Workflow Readiness Panels

Phase 26 adds lightweight workflow guidance to key admin detail pages.

## Participant Detail

The participant detail page now shows readiness checks for:

- NDIS number recorded.
- Plan dates recorded.
- Active worker assignment.

It also includes shortcuts to:

- Assign Worker.
- Upload Document.
- Create Shift.

## Support Worker Detail

The support worker detail page now shows readiness checks for:

- Worker active.
- Police check current.
- WWCC / Blue Card current.
- Active participant assignment.

It also includes shortcuts to:

- Edit Worker.
- Upload Document.
- Create Shift.

## Shift Detail

The shift detail page now shows a workflow status panel for:

- Draft.
- Published.
- Confirmed.
- Completed.
- Cancelled.
- No show.

The panel explains the likely next step and links to relevant existing actions.

## Shortcut Prefill

The following shortcut links can prefill existing forms:

- `documents/new/?participant=<id>`
- `documents/new/?worker=<id>`
- `roster/new/?participant=<id>`
- `roster/new/?worker=<id>`

This keeps the workflow fast without adding new database fields or new permissions.
