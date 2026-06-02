# Phase 40 Roster Name Filters Design

## Goal

Make roster filtering scalable for larger participant and worker lists by using name search instead of database IDs.

## Scope

- Filter roster shifts by participant first name or last name.
- Filter roster shifts by worker first name or last name.
- Show Participant and Worker search fields in the roster filter form.
- Preserve date and status filters.
- Keep filter summary text aligned with the entered search keywords.

## Behavior

- Typing `Ava` in Participant matches participants with `Ava` in first or last name.
- Typing `Wendy` in Worker matches support workers with `Wendy` in first or last name.
- The system no longer expects users to know worker or participant IDs on the roster list.

## Out Of Scope

- Autocomplete dropdowns.
- Phone, email, or NDIS number matching.
- Changes to shift creation or assignment logic.
