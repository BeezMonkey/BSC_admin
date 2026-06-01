# Phase 28 Service Log Invoice Shortcut Plan

## Steps

1. Add a failing test for the Approved service log Create Invoice shortcut.
2. Add the shortcut action to Approved rows in the service log list.
3. Keep Submitted, Rejected, and Invoiced rows without the shortcut.
4. Reuse the existing invoice create preview flow with query string prefill.
5. Run targeted invoice/service log tests, full Django tests, and system checks.

## Acceptance

- Approved service logs show a Create Invoice action.
- The action opens invoice creation with participant and same-day period prefilled.
- Non-approved service logs do not show the shortcut.
- Existing invoice generation tests continue to pass.
