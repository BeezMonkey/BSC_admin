# Phase 11 Recurring Shifts Design

## Goal

Phase 11 adds simple recurring shift creation for common weekly and fortnightly schedules. Admin users can preview the generated dates, see worker conflicts, and create only the non-conflicting draft shifts.

## Scope

This phase includes:

- Recurring shift form from the roster area.
- Weekly and fortnightly frequency.
- Preview before creation.
- Worker conflict detection using existing active shift statuses.
- Batch creation of draft shifts.
- Created and skipped counts after confirmation.

This phase does not include drag-and-drop calendars, multiple weekdays, recurring series management, automatic worker assignment, or editing/deleting a whole recurrence series.

## Flow

Admins enter participant, worker, service date range, time, break, support item, service type, location, address, and notes. The preview lists each generated service date as either:

- `Will create`
- `Skipped - worker conflict`

Submitting the same form with confirmation creates one draft `Shift` for each non-conflicting date. Conflicting dates are skipped.

## Rules

- Frequency can be weekly or fortnightly.
- End date must be on or after start date.
- End time must be after start time.
- Planned hours must be greater than zero after break.
- All generated shifts are created as draft.
- Draft shifts participate in conflict checks, matching the existing Phase 6 behavior.

## Tests

Tests cover:

- Weekly preview lists generated dates.
- Fortnightly preview skips alternate weeks.
- Existing active worker conflict is shown as skipped.
- Confirm creates only non-conflicting draft shifts.
- Worker users cannot access recurring shift creation.
