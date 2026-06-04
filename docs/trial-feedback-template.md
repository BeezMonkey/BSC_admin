# Trial Feedback Template

Use this template when collecting feedback from staff, friends, or staging testers. Ask testers to copy one template per issue or suggestion.

Do not include real participant names, NDIS numbers, addresses, phone numbers, private documents, or sensitive notes in feedback.

## Quick Feedback Form

```text
Feedback type:
Role used:
Test ID:
Page URL:
Device/browser:
Date/time:

What I was trying to do:

Steps I took:
1.
2.
3.

Expected result:

Actual result:

Business impact:

Screenshot attached:
Yes / No

Did this create or change test data?
Yes / No / Not sure

Suggested improvement:
```

## Feedback Type

Choose one:

- Bug: something failed, blocked, or behaved incorrectly.
- Usability: the workflow worked but felt confusing or slow.
- Layout: spacing, alignment, mobile display, or visual clarity issue.
- Data: missing field, wrong label, unclear value, or incorrect format.
- Workflow gap: a real business step is missing.
- Suggestion: improvement idea, not blocking.

## Severity

Use this scale:

| Severity | Meaning | Example |
| --- | --- | --- |
| Critical | Blocks safe trial use | User can see the wrong participant data |
| High | Blocks a core workflow | Worker cannot submit a service log |
| Medium | Workflow can continue with workaround | Invoice can be created, but filter is confusing |
| Low | Cosmetic or small wording issue | Button spacing or label polish |

## Good Feedback Examples

Good:

```text
Feedback type: Usability
Role used: Admin
Test ID: I04
Page URL: /invoices/new/
Device/browser: Chrome on Windows laptop

What I was trying to do:
Preview approved service logs for Ava Nguyen.

Steps I took:
1. Opened Invoices.
2. Clicked Create Invoice.
3. Selected Ava Nguyen and June dates.
4. Clicked Preview Logs.

Expected result:
I expected the approved logs to be easy to identify and select.

Actual result:
The logs appeared, but it was hard to tell which service date I had selected.

Business impact:
Medium. I could continue, but I might pick the wrong log.

Screenshot attached:
Yes

Did this create or change test data?
No

Suggested improvement:
Make selected rows more obvious or add a count of selected logs.
```

Not enough detail:

```text
Invoice page is confusing.
```

## Tester Instructions

- Use test or staging data only.
- Include the test ID from `docs/staging-smoke-test-matrix.md` when possible.
- Include the exact page URL.
- Include your role, such as Admin, Worker, or Accountant.
- Add a screenshot for layout or visual problems.
- Say whether you created or changed any data.
- Report one issue per template so each item can be tracked separately.

## Internal Triage Notes

When reviewing feedback:

- Confirm whether it is reproducible.
- Confirm whether it affects local only, staging only, or both.
- Classify it as bug, usability, layout, data, workflow gap, or suggestion.
- Assign severity.
- Decide whether it belongs before staging, before production, or after V1.
- If the item needs code work, create a separate phase or issue for it.
