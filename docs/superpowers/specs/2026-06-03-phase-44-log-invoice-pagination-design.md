# Phase 44: Service Log and Invoice Pagination Design

## Purpose

Service Logs and Invoices will grow quickly during normal operations. These lists should use the same pagination behavior introduced for Participants, Support Workers, and Roster so admins can scan high-volume records without long pages.

## Scope

- Add pagination to the admin Service Logs list.
- Add pagination to the Invoices list.
- Preserve active filters when moving between pages.
- Reuse the shared pagination helper and template from Phase 43.
- Keep existing Service Log review, bulk invoice selection, invoice creation, invoice actions, and export behavior unchanged.

## Out Of Scope

- No new filters.
- No page size selector.
- No advanced sorting.
- No workflow changes for approving logs or generating invoices.

## Expected Result

Admins and finance users see the first 20 matching Service Logs or Invoices, a visible record range, and next/previous pagination links that keep the current filter state.
