# Unscheduled Service Design

## Goal

Allow support workers to submit a completed service when there was no admin-created rostered shift, while keeping admin review, attachments, PDF download, roster visibility, and invoice preparation on the existing service log path.

## Scope

This first version adds only Unscheduled Service. It does not add Open Shifts, worker self-assignment, availability, or a new scheduling marketplace.

## User Flow

Workers can start an unscheduled service log from Home or My Logs. The form asks for participant, service date, actual start and end time, break, kilometres, support item, case notes, worker notes, a required reason for the unscheduled service, and optional attachments using the existing three-file upload interaction.

On submit, the worker sees a success message and lands on the worker service log detail page.

## Data Model

The system keeps `ServiceLog.shift` required. For each unscheduled submission it creates a backing `Shift` marked as unscheduled, with the current worker user as `created_by`, `status=completed`, and `completed_at` set at submission time. `ServiceLog` stores an explicit source of scheduled or unscheduled, plus the unscheduled reason.

## Admin Flow

Admin Service Logs use the existing submitted, approved, rejected, and invoiced states. Unscheduled records show an `Unscheduled` marker on the service log detail, the roster list, and the downloaded PDF. Approved unscheduled service logs remain invoice-ready through the existing approved service log selection.

## Validation

Workers may only choose active participants assigned to them through active participant-worker assignments. Time and attachment validation reuse the existing service log rules. The unscheduled reason is required.

