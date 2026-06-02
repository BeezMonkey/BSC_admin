# Phase 38 Multi-Filter Summary Design

## Goal

Make active filter summaries more useful when list pages are filtered by more than status.

## Scope

- Expand Roster filter summaries to include status, worker, and date range.
- Expand Invoice filter summaries to include status, invoice query, participant query, and period range.
- Keep Service Logs unchanged because it currently only has a status filter.
- Preserve all existing filtering behavior and clear filter links.

## Example Text

- `Showing published shifts for Wendy Worker from June 1, 2026 to June 30, 2026.`
- `Showing draft invoices matching "0001" for Ava from June 1, 2026 to June 30, 2026.`

## Out Of Scope

- Adding new filters.
- Changing query behavior.
- Changing table actions or dashboard metrics.
