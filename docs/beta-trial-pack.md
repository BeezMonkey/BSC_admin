# Brisbane Star Care Beta Trial Pack

Use this pack for the first small online beta trial of the Brisbane Star Care NDIS admin system.

The beta site is for workflow feedback only. Use fake or anonymized data until backup, privacy handling, and production procedures are confirmed.

## Beta Site

```text
https://bsc-admin-beta.onrender.com/login/
```

Health check:

```text
https://bsc-admin-beta.onrender.com/health/
```

Expected health response:

```json
{"status": "ok"}
```

## Trial Documents

- Tester guide: `docs/beta-tester-guide.md`
- Feedback log: `docs/beta-feedback-log.md`
- Detailed smoke test matrix: `docs/staging-smoke-test-matrix.md`
- Feedback issue template: `docs/trial-feedback-template.md`
- Render handoff checklist: `docs/render-beta-handoff-checklist.md`

## Seeded Beta Accounts

These accounts are for beta workflow testing only.

| Role | Username | Purpose |
| --- | --- | --- |
| Worker | `beta_worker` | Worker portal, shift confirmation, service log submission |
| Accountant | `beta_accountant` | Invoice review and finance workflow checks |

The temporary password is set when running:

```text
python manage.py seed_beta_test_data --password <temporary-test-password>
```

Do not publish passwords in shared documents or screenshots.

## Current Smoke-Tested Workflow

The online beta has already passed this workflow once:

1. Admin viewed seeded participant, worker, and roster records.
2. Worker logged in.
3. Worker confirmed a published shift.
4. Worker submitted a service log.
5. Admin approved the service log.
6. Admin created an invoice.
7. CSV and PDF invoice downloads were manually checked.

## First Trial Scope

Ask testers to focus on:

- Whether the login and navigation make sense.
- Whether the admin workflow matches normal office operations.
- Whether worker pages are clear enough for shift and service log tasks.
- Whether invoice creation is understandable.
- Which fields are missing or unclear.
- Any visual layout issues on their device.

Do not ask testers to evaluate:

- Final branding.
- Payroll integration.
- SMS/email notifications.
- Full NDIS claiming automation.
- Real document storage.

Those are later stages.

## Data Safety Rules

Do not enter:

- Real participant names.
- Real NDIS numbers.
- Real addresses.
- Real phone numbers.
- Real medical, support, behaviour, or risk notes.
- Real plan manager details.
- Real invoices or claim data.
- Real worker compliance documents.

Use clearly fake data such as:

```text
Beta Participant
990000001
10 Test Street
beta.participant@example.com
```

## Recommended Trial Group

Start with:

- 1 admin tester.
- 1 worker tester.
- Optional 1 finance/accounting tester.

Keep the first trial small so feedback is easy to understand and the database stays tidy.

## Trial Completion Criteria

The first beta trial is useful if testers can answer:

- Can they log in without help?
- Can they find their next task?
- Can they complete the test workflow?
- Where did they hesitate?
- Which labels or fields felt unclear?
- What is missing before real staff use?

Record answers in `docs/beta-feedback-log.md`.
