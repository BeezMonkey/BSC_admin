# Phase 45: List Sorting Basics Design

## Purpose

After adding pagination to high-volume admin lists, users need basic sorting so records can be found by meaningful columns instead of relying on default database order.

## Scope

- Add safe, whitelisted sorting to Participants, Support Workers, Roster, Service Logs, and Invoices.
- Use table header links for sortable columns.
- Preserve current filters when switching sort direction.
- Preserve sort parameters during pagination through the existing pagination helper.
- Support Invoice sorting by calculated total using a query annotation.

## Sortable Columns

- Participants: Name, Status.
- Support Workers: Name, Type, Status.
- Roster: Date, Participant, Worker, Status.
- Service Logs: Date, Participant, Worker, Status.
- Invoices: Invoice, Participant, Period, Status, Total.

## Out Of Scope

- No new filters.
- No page size selector.
- No client-side sorting.
- No data model changes.
- No business workflow changes.

## Expected Result

Admin and finance users can click supported table headers to sort lists ascending or descending while keeping their current filters and pagination behavior intact.
