# Phase 49 Create Return State Design

## Goal
Preserve list context when admins create new Participants, Support Workers, or Roster shifts from a filtered list.

## Scope
This phase covers the core create flows reachable from filtered admin lists:

- Participants list to Add Participant
- Support Workers list to Add Worker
- Roster list to New Shift

## Behavior
List-level create buttons include the current list URL as a safe `next` target. Create forms use that target for Cancel links and include it in a hidden field for POST submissions. Successful creates return to the supplied safe list URL. When no safe return target is supplied, existing behavior remains unchanged and the user is redirected to the newly-created record detail page.

## Safety
The implementation reuses `get_safe_return_url`, so external or unsafe return targets are ignored.

## Testing
Tests cover create button links, form cancel and hidden return fields, successful create redirects with `next`, and existing default create redirects without `next`.
