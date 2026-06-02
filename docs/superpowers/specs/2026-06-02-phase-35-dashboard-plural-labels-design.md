# Phase 35 Dashboard Plural Labels Design

## Goal

Polish admin dashboard summary labels so counts use natural English singular and plural wording.

## Scope

- Convert operations summary count text from fixed singular wording to generated labels.
- Preserve existing dashboard links, counts, and workflow behavior.
- Cover plural labels with regression tests.

## Label Rules

- A count of 1 uses the singular label, such as `1 draft shift`.
- Counts other than 1 use the plural label, such as `2 draft shifts`.
- Labels are generated in the view so templates stay simple.

## Out Of Scope

- Changing dashboard layout.
- Changing the underlying operations summary counts.
- Changing worker shift status wording.
