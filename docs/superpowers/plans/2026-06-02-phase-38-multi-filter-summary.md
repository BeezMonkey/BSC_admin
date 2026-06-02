# Phase 38 Multi-Filter Summary Plan

## Implementation Steps

1. Add focused tests for Roster and Invoice multi-filter summaries.
2. Add date formatting helpers for filter summary text.
3. Build Roster summaries from status, worker, and date filters.
4. Build Invoice summaries from status, invoice query, participant query, and period filters.
5. Run focused, module, system, and full Django verification.

## Verification

- Existing status-only summaries still work.
- Multi-condition Roster summaries include worker and date range.
- Multi-condition Invoice summaries include query, participant, status, and period range.
- No filtering behavior changes.
