# Phase 26 Workflow Readiness Panels Design

## Purpose

Phase 26 adds small workflow guidance panels to key detail pages so admins can quickly see readiness status and likely next actions.

## Scope

- Participant detail readiness and next-step shortcuts.
- Support worker detail readiness and next-step shortcuts.
- Shift detail workflow status and next-step shortcuts.
- Query-parameter prefill for document upload and shift creation shortcuts.
- Styling for readiness and workflow panels.

## Out Of Scope

- Database changes.
- Permission changes.
- New status fields.
- Notification delivery.
- Calendar roster UI.
- Full dashboard redesign.

## Approach

Use existing model fields and relationships to calculate readiness in the view layer. Render the guidance as cards inside existing detail pages. Keep shortcuts as ordinary links to existing pages, with lightweight query-parameter prefill where the target form already supports the linked record.

## Verification

- Add focused tests for readiness panel content.
- Add focused tests for shortcut prefill.
- Run relevant app tests.
- Run the full Django test suite before completion.
