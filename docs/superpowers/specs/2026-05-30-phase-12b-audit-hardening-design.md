# Phase 12B Audit Hardening Design

## Goal

Phase 12B adds a lightweight audit trail for key business actions. The goal is traceability without storing sensitive file contents or complex field diffs.

## Scope

This phase includes:

- `AuditLog` model.
- Helper function for consistent audit creation.
- Admin audit log list and detail pages.
- Worker access blocked from audit logs.
- Audit records for:
  - service log approve
  - service log reject
  - shift cancel
  - invoice create
  - invoice mark issued
  - invoice mark paid
  - invoice cancel
  - document upload
  - document download

This phase does not include full diff history, audit export, retention policy, login tracking, production backup automation, or PostgreSQL deployment changes.

## Data Model

`AuditLog` stores:

- `actor`
- `action`
- `object_type`
- `object_id`
- `summary`
- `created_at`

`actor` can be null so future system actions can also be recorded.

## Admin Flow

Admins can open `/audit-logs/` to see recent audit records and open a detail page. Workers cannot access the audit log pages.

## Recording Rules

Each audited action writes one record after the business action succeeds. The summary should be human-readable and avoid sensitive contents such as uploaded file bytes.

## Tests

Tests cover:

- Approving service log writes audit record.
- Rejecting service log writes audit record.
- Cancelling shift writes audit record.
- Creating invoice writes audit record.
- Invoice status changes write audit records.
- Document upload and download write audit records.
- Admin can view audit log list and detail.
- Worker cannot view audit logs.
