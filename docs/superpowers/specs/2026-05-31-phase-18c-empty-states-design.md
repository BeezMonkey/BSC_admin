# Phase 18C Empty States Design

Phase 18C improves V1 trial guidance by making empty list pages more helpful. It does not change data, permissions, or workflows.

## Goals

- Replace terse empty messages with short guidance.
- Add next-step actions where a safe create action already exists.
- Keep table structure valid on admin list pages.
- Improve worker-facing empty states without adding new routes.

## Non-goals

- No model changes.
- No database migrations.
- No new business workflow.
- No permission changes.
- No JavaScript interactions.

## Acceptance Criteria

- Admin list pages explain what to do when empty.
- Worker empty pages explain why no records appear yet.
- Existing create/upload links are reused.
- Tests and system checks pass.
