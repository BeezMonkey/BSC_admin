# Phase 46: Empty State Filter Feedback Design

## Purpose

Admin users should be able to tell whether a list is truly empty or whether the current filters returned no matches. This reduces confusion when searching, filtering, sorting, and paginating larger data sets.

## Scope

- Update Participants, Support Workers, Roster, Service Logs, and Invoices empty states.
- Show a filter-specific message when active filters produce no results.
- Keep the original creation-oriented empty state when no records exist and no filters are active.
- Add a clear filters action for filtered empty states.

## Out Of Scope

- No new filters.
- No workflow changes.
- No data model changes.
- No pagination or sorting behavior changes.

## Expected Result

When a user filters a list and no records match, the page says the current filters have no matches and provides a clear filters action. When there are no records at all, the page keeps the existing guidance to create the first record.
