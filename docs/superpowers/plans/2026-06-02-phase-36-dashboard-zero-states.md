# Phase 36 Dashboard Zero States Plan

## Implementation Steps

1. Add dashboard tests for all-zero admin and worker summary states.
2. Add view context flags for whether summary action items exist.
3. Render summary tiles only when action items exist.
4. Render concise empty-state messages when all summary counts are zero.
5. Add shared empty-state styling.
6. Run focused and full Django verification.

## Verification

- Admin dashboard zero state hides `0 ...` summary tiles.
- Worker dashboard zero state hides `0 ...` shift summary tiles.
- Existing non-zero summary tests remain green.
