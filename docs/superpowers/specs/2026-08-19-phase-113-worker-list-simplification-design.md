# Phase 113: Support Worker List Simplification

## Goal

Make the Support Workers list easier to scan as worker numbers grow, without changing worker records, compliance data, permissions, or business workflows.

## Scope

- Remove the `Compliance` column from the Support Workers list.
- Keep the existing columns for name, email, phone, employment type, worker status, and actions.
- Keep Police Check and WWCC fields unchanged on Worker View and Edit pages.
- Preserve all existing search, status filtering, employment type filtering, pagination, URLs, and permissions.

## Behaviour

The list remains an operational directory for finding workers and checking whether they are active for rostering. Compliance details remain available in the worker record and are not deleted or recalculated.

`Status` continues to represent the SupportWorker roster status. Account login access continues to be managed separately through the existing account-active field on the Worker View/Edit flow.

## Files

- Update `templates/workers/worker_list.html` to remove the header and row cell.
- Update focused worker list tests only where needed to protect the simplified table contract.

## Exclusions

- No database migrations or model changes.
- No changes to Worker View or Edit pages.
- No changes to compliance validation or document management.
- No changes to roster eligibility or login access behaviour.
- No broader visual redesign.

## Verification

- Worker list renders without a Compliance column or inline Police/WWCC summary.
- Worker detail and edit pages still expose the existing compliance information.
- Search and filters continue to work.
- Worker tests and `manage.py check` pass.
