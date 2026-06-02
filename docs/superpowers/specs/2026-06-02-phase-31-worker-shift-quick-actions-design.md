# Phase 31 Worker Shift Quick Actions Design

## Goal

Make the worker My Shifts page more actionable by showing the next useful action directly in the list.

## Scope

- Published shifts show a Confirm action in the list.
- Confirmed shifts show a Complete Log action in the list.
- Completed/history shifts keep View only.
- Existing detail page actions remain unchanged.

## Behaviour

Confirm uses the existing worker shift confirmation POST endpoint.

Complete Log links to the existing worker service log creation page.

No action is shown for completed, cancelled, or no-show shifts beyond View.

## Non-goals

- No new shift status transitions.
- No one-click service log completion.
- No changes to worker permissions.
