# Phase 23 UI QA Pass Design

## Purpose

Phase 23 performs a browser-oriented visual QA pass after the Phase 22 shared CSS polish. The goal is to catch small layout regressions before continuing with larger UI work.

## Scope

- Inspect representative admin list pages.
- Inspect representative worker pages.
- Fix small visual inconsistencies caused by shared CSS.
- Keep changes limited to CSS or documentation unless a template issue is clearly identified.

## Out Of Scope

- Full template redesign.
- New business features.
- Permission or routing changes.
- Database changes.
- Third-party admin template integration.

## QA Focus

- Button height consistency.
- Filter bar alignment.
- Table edge and row border consistency.
- Actions column spacing.
- Empty state spacing.
- Worker shell readability.

## Verification

- Run Django system checks.
- Run browser smoke checks on representative pages.
- Run tests if any templates or Python code change.
