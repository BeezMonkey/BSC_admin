# Local Demo Data

Use this guide to prepare a local V1 trial database. These records are for local testing and demonstration only.

## Prepare the database

```powershell
python manage.py migrate
python manage.py seed_demo_data
```

The seed command is safe to run more than once. It reuses stable demo records instead of creating duplicate users, participants, shifts, service logs, or invoices.

## Demo logins

```text
admin / BscTest123!
worker / BscTest123!
accountant / BscTest123!
```

Do not use these credentials in production.

## Seeded workflow

The command prepares:

- Admin, worker, and accountant trial accounts.
- Two active participants: Ava Nguyen and Ben Taylor.
- One active support worker: Wendy Worker.
- Two active participant-worker assignments.
- One active hourly support item.
- Two completed shifts on June 1 and June 2, 2026.
- Two invoiced service logs linked to those shifts.
- Two draft invoices: `DEMO-202606-0001` and `DEMO-202606-0002`.

## Suggested local pages

Admin:

```text
http://127.0.0.1:8000/admin-dashboard/
http://127.0.0.1:8000/participants/
http://127.0.0.1:8000/workers/
http://127.0.0.1:8000/roster/
http://127.0.0.1:8000/service-logs/
http://127.0.0.1:8000/invoices/
```

Worker:

```text
http://127.0.0.1:8000/sw/dashboard/
http://127.0.0.1:8000/sw/shifts/
http://127.0.0.1:8000/sw/logs/
http://127.0.0.1:8000/sw/profile/
```

Accountant:

```text
http://127.0.0.1:8000/invoices/
http://127.0.0.1:8000/exports/
```
