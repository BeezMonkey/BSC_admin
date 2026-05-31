# Phase 15 Demo Readiness Design

Phase 15 prepares the local V1 system for repeatable trial use. It adds a safe local demo-data setup path so the browser can be tested without manually recreating accounts, participants, workers, shifts, service logs, and invoice examples.

## Goals

- Add a repeatable Django management command for local demo data.
- Create predictable local trial accounts for admin, worker, and accountant roles.
- Seed a small connected data set covering the main V1 workflow.
- Document how to prepare local trial data.
- Add tests proving the command can run more than once without duplicating key records.

## Non-goals

- No production data import.
- No NDIS official CSV import.
- No deployment changes.
- No UI redesign.
- No permission rule changes.
- No model changes or migrations unless an existing model requires it.
- No destructive database reset command.

## Command

Add:

```powershell
python manage.py seed_demo_data
```

The command should be idempotent. Running it repeatedly updates or reuses known demo records instead of creating duplicates.

## Demo Accounts

Create or update:

- `admin / BscTest123!` with `admin` role.
- `worker / BscTest123!` with `support_worker` role and a linked support worker profile.
- `accountant / BscTest123!` with `accountant` role.

These accounts are for local trial only. Documentation must say they should not be used in production.

## Demo Business Data

Seed a minimal but connected set:

- One active participant.
- One active support worker linked to `worker`.
- One active participant-worker assignment.
- One active hourly support item.
- One published or completed shift.
- One approved service log linked to the shift.
- One draft invoice with an invoice line when supported by existing models.

The seeded records should use stable identifiers such as fixed usernames, NDIS number, support item number, and invoice period so tests can assert idempotency.

## Safety

- The command must not delete user-created records.
- The command must not alter unrelated users with different usernames.
- The command must not require external network access.
- The command should print a concise summary of created or updated records.

## Documentation

Add a local trial data guide with:

- Command to run migrations.
- Command to seed demo data.
- Trial login credentials.
- Suggested pages to open after seeding.
- Warning that demo credentials are not for production.

## Testing

Add tests for:

- Command creates role profiles and key business records.
- Command can run twice without duplicating stable records.
- Worker account has a linked `SupportWorker`.
- Service log and invoice line connect to the seeded shift and support item.

## Acceptance Criteria

- `python manage.py seed_demo_data` runs successfully on a migrated local database.
- Re-running the command is safe.
- Demo login credentials are documented.
- Existing test suite continues to pass.
