# Phase 52C Table and List Polish Design

## Goal
Improve the daily admin list-view experience with clearer tables, actions, hover states, and pagination.

## Scope
This phase only refines existing visual styles:

- Table container
- Table header and row states
- Action links inside table cells
- Bulk action spacing
- Pagination controls
- Empty state spacing

## Safety Rules
This phase must not copy Tabler code or import Tabler assets. It must not change query parameters, URLs, form field names, view logic, permissions, models, or table data.

## Implementation
Changes live in `static/css/app.css`. Existing template structure and class names remain in place.

## Testing
Existing list tests verify records, links, filters, sorting, and pagination still work. A lightweight regression test verifies the pagination structure remains available on paginated lists.
