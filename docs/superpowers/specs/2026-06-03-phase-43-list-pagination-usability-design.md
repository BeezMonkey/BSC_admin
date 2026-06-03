# Phase 43: List Pagination Usability Design

## Purpose

Core admin lists should stay usable when Brisbane Star Care has many participants, workers, or roster items. Admin users need a predictable page size and simple next/previous navigation without losing active filters.

## Scope

- Add pagination to Participants, Support Workers, and Roster lists.
- Show a visible record range such as `Showing 1-20 of 25 records`.
- Preserve current search and filter query parameters when moving between pages.
- Use a shared helper and shared pagination template so later lists can reuse the same pattern.

## Out Of Scope

- No business workflow changes.
- No database model changes.
- No advanced sorting, saved views, or page size selector.
- No pagination changes for Service Logs or Invoices in this phase.

## Expected Result

Admins can work with larger lists without long pages, and they can move to the next or previous page while keeping the same search and filter criteria.
