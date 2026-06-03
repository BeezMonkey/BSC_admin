# Phase 42: Roster Expanded Keyword Filters Design

## Purpose

Roster filtering should stay simple for daily admin use while handling real lookup habits. Admin users may know a participant NDIS number, a participant phone number, a worker email, or a worker phone number instead of the exact display name.

## Scope

- Extend the existing Participant keyword filter on the Roster page to match participant first name, last name, NDIS number, and phone.
- Extend the existing Worker keyword filter on the Roster page to match worker first name, last name, email, and phone.
- Update the filter input placeholders so admins can see what each field accepts.
- Keep the current Roster layout, query parameter names, status/date filters, and filter summary behavior.

## Out Of Scope

- No advanced autocomplete.
- No pagination or saved searches.
- No participant or worker list behavior changes.
- No shift creation, recurring shift, or invoice workflow changes.

## Expected Result

An admin can open Roster and use one Participant field or one Worker field for common identifiers. For example, searching a participant's NDIS number or a worker's email should return the matching shifts without needing internal database IDs.
