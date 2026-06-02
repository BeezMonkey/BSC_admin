# Phase 36 Dashboard Zero States Design

## Goal

Make dashboard summaries quieter and clearer when there are no current action items.

## Scope

- Show the existing summary tiles when admin or worker action counts are non-zero.
- Replace all-zero admin summary tiles with a short zero-state message.
- Replace all-zero worker shift summary tiles with a short zero-state message.
- Keep existing links, counts, and workflow behavior unchanged when action items exist.

## Zero-State Text

- Admin dashboard: `No outstanding admin actions.`
- Worker dashboard: `No shift actions need attention.`

## Out Of Scope

- Changing how counts are calculated.
- Changing dashboard navigation cards.
- Adding notifications or reminders.
