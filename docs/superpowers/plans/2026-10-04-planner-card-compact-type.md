# Planner Card Compact Type

## Approved Scope

Local preview only. Reduce card typography by approximately 8%, keep am/pm,
existing hierarchy, spacing, separators, colours and action target dimensions.
Allow long status labels to wrap fully. Apply through the shared Planner styles
in Daily, Participant and Worker views. No business logic, holiday data, portal
styles, staging deployment or Main changes.

## Implementation

- [x] Confirm the clipping cause and current computed sizes in the local browser.
- [x] Add focused style regression tests and verify they fail before the fix.
- [x] Adjust only the Planner typography and status wrapping rules.
- [x] Run focused Django/JavaScript tests and inspect all three Planner views.
- [x] Check desktop/mobile layouts and unchanged action target sizes.
- [x] Open the local preview with synthetic demo shifts; do not push.

## Baseline

At the local preview viewport, time is 13.12px, names are 12.48px and statuses
are 12px. Action targets are 26.4px wide. A 131.54px Cancellation review badge
overflows a 122.58px tile because the shared status style forbids wrapping.

## Verification

- 213 Django scheduling/theme tests passed, including three new style tests.
- 18 JavaScript calendar tests passed.
- Local browser checks passed in all three views at 390px and 1440px, plus
  Daily/Worker at 320px and Daily at the existing 968px viewport.
- Computed time/name/status sizes are 12.16px / 11.52px / 11.04px, respectively.
  Action targets remain 26.4px square. Long status labels stay within the tile.
- Reused the isolated local preview database; three synthetic shifts show
  Confirmed, Cancelled and Cancellation review. No staging/production data changed.
- Local preview uses collected, fingerprinted assets to avoid stale CSS caches.

## Approved Follow-Up: Regular Time and Tighter Text

Time uses 400 weight and 0.72rem (matching names). Text-row gap changes from
0.32rem to 0.25rem, and time/name line heights change from 1.4 to 1.3.
Separator/footer spacing, status styles, action targets and all business logic
remain unchanged. This supersedes the initial time hierarchy/spacing choice.

- [x] Update the focused style tests and confirm the expected failures.
- [x] Change the four shared Planner text rules only.
- [x] Run focused tests; collect assets and refresh the isolated local server.
- [x] Verify three views on desktop/mobile, save a screenshot and leave the local
  preview open. Do not push or deploy.

Follow-up verification: 215 Django scheduling/theme tests passed. All three
Planner views passed browser checks at 1159px and 390px. Time is 11.52px at
weight 400 with 14.976px line height; text gap is 4px. Action targets remain
26.4px square, footer gap remains 6.4px and footer top padding remains 7.2px.
Long status labels still fit their cards. No records were changed this round.

## Approved Follow-Up: Compact am/pm and Semibold Time

Use `9:00am - 12:00pm` in the shared Planner card only. Keep the 0.72rem size
and all current spacing. Time weight changes from 400 to 600, superseding the
previous regular-weight choice. The shared time formatter, tooltip, stored
times and all other screens remain unchanged.

- [x] Confirm the new semibold and three-view compact-time tests fail first.
- [x] Apply the built-in `cut` filter only to the Planner time spans and set
  the card time weight to 600.
- [x] Run regressions and verify the local preview; do not push or deploy.

Verification: 215 Django scheduling/theme tests passed. Browser checks passed
in all three views at 1280px and 390px: `9:00am` / `12:00pm`, 11.52px size,
weight 600, unchanged 4px text gap, no time/status overflow. Local preview and
the screenshot were refreshed. No data changes or remote deployment.

## Release Preparation

The user approved pushing a feature branch and opening a PR targeting staging.
Main remains unchanged, and neither branch is to be merged automatically.

- Base verified against latest `origin/staging`: `439a830d54820b75fe8a69e791c29012fd7edcda`.
- Full Django suite: 814 tests, 813 passed and one PostgreSQL row-lock test
  skipped on local SQLite. JavaScript suite: all 18 tests passed.
- Code review scope: shared Planner template and its opt-in stylesheet only;
  no pricing, status transitions, permissions, time storage, shared formatter,
  holiday data, models or migrations changed.
- Commit only the two runtime files, two test files and this implementation
  record. Exclude local prototypes, screenshots, preview scripts and databases.
