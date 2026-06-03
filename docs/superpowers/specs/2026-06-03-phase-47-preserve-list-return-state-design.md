# Phase 47: Preserve List Return State Design

## Purpose

Users often filter, sort, or paginate a list before opening a record. After reviewing the record detail page, the Back action should return to the same list state instead of resetting the list.

## Scope

- Add a `next` return URL to View links from Participants, Support Workers, Roster, Service Logs, and Invoices lists.
- Use the `next` return URL for the detail page Back button when it is safe.
- Fall back to the normal list route when no safe return URL is supplied.
- Keep existing edit, action, approval, invoicing, export, and workflow behavior unchanged.

## Safety

The detail page only uses `next` when it points to the same host or a safe relative URL. External URLs are ignored.

## Out Of Scope

- No form cancel behavior changes.
- No workflow redirect changes after post actions.
- No data model changes.
- No browser history manipulation.

## Expected Result

When a user opens a record from a filtered, sorted, or paginated list and clicks Back on the detail page, they return to that same list URL.
