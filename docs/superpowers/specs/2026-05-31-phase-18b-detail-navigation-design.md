# Phase 18B Detail Navigation Polish Design

Phase 18B improves trial usability by adding clear back-navigation actions on detail pages. It does not change business workflows.

## Goals

- Add obvious `Back to ...` links on admin detail pages.
- Add obvious worker-facing return links on worker detail pages.
- Keep existing primary actions such as Edit, Download, Approve, and Cancel.
- Avoid changing URLs, permissions, forms, models, or view logic.

## Scope

Update detail templates for participants, workers, shifts, service logs, invoices, documents, support items, audit logs, and worker-facing shift/log/document pages.

## Acceptance Criteria

- Detail pages include a clear return link to their list page.
- Existing action buttons remain available.
- Template tests and full app tests pass.
