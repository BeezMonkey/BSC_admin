# Phase 25 Business Workflow Review Design

## Purpose

Phase 25 reviews the current V1 business workflow from an NDIS operations perspective before adding more features, deployment work, or larger UI theme changes.

## Scope

- Review participant onboarding.
- Review support worker onboarding.
- Review participant-worker assignment.
- Review roster creation, publishing, confirmation, and completion.
- Review worker service log submission.
- Review admin service log review.
- Review invoice creation and status progression.
- Review document handling.
- Review audit log coverage.
- Identify practical next-step improvements.

## Out Of Scope

- New features or code changes.
- Database model changes.
- Permission changes.
- UI theme integration.
- Production deployment.

## Approach

Use the current models, views, templates, and V1 documentation to describe the end-to-end workflow. Separate findings into working V1 flows, friction points, and suggested future phases.

## Expected Result

The project should have a clear business workflow review document that helps decide whether the next work should focus on workflow shortcuts, missing fields, reporting, notifications, or continued UI polish.

## Verification

This is documentation-only. Run Django system checks to confirm the project still loads.
