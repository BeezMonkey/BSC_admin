# Beta Tester Guide

This guide is for people testing the Brisbane Star Care NDIS admin system beta.

The beta is not production. Use fake data only.

## Login

Open:

```text
https://bsc-admin-beta.onrender.com/login/
```

Use the test account provided by the Brisbane Star Care admin.

Do not share passwords in screenshots, emails, or feedback notes.

## Important Safety Rule

Do not enter real client, worker, invoice, or NDIS information.

Use fake names, fake phone numbers, fake addresses, and fake notes.

## Worker Test Steps

Use these steps when testing as a worker.

1. Log in with the worker test account.
2. Open `My Shifts`.
3. Find a shift that needs attention.
4. Open the shift.
5. Confirm the shift.
6. Complete the service log.
7. Add short fake case notes.
8. Submit the service log.
9. Open `My Logs` and confirm the submitted log appears.
10. Open `Profile` and check whether the information layout is understandable.

Report:

- Anything confusing.
- Any missing field.
- Any wording that does not match normal work.
- Any layout problem on your device.

## Admin Test Steps

Use these steps when testing as an admin.

1. Open `Dashboard`.
2. Open `Participants` and check the list.
3. Open `Support Workers` and check the list.
4. Open `Roster` and check the shift.
5. Open `Service Logs`.
6. View a submitted service log.
7. Approve the service log.
8. Open `Invoices`.
9. Create an invoice from approved logs.
10. Open the invoice detail page.
11. Download CSV and PDF.
12. Open `Audit Logs` and confirm recent actions appear.

Report:

- Any workflow step that feels too slow.
- Any page where the next action is unclear.
- Any missing filter or field.
- Any incorrect date, amount, or status.

## Finance Test Steps

Use these steps when testing invoice workflow.

1. Log in with the finance or accountant test account.
2. Open `Invoices`.
3. Filter invoices by status or date where available.
4. Open an invoice.
5. Check invoice period, participant, line item, quantity, unit price, and total.
6. Download CSV.
7. Download PDF.

Report:

- Any incorrect currency formatting.
- Any unclear invoice status.
- Any missing export field.
- Any issue with CSV or PDF downloads.

## Feedback Format

For each issue, capture:

```text
Role used:
Page URL:
What you tried to do:
Steps:
Expected result:
Actual result:
Impact:
Screenshot attached: Yes / No
Suggested improvement:
```

One issue per note is best.

## What Good Feedback Looks Like

Good:

```text
Role used: Worker
Page URL: /sw/shifts/
What I tried to do: Confirm my assigned shift.
Steps: Logged in, opened My Shifts, opened the shift, clicked Confirm.
Expected result: I expected the shift to move out of Needs attention.
Actual result: It worked, but I did not notice the success message at first.
Impact: Low. Workflow works, but the confirmation could be more obvious.
Suggested improvement: Make the success message more visible.
```

Not enough:

```text
Shift page is confusing.
```
