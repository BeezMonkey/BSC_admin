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
- One active participant: Ava Nguyen.
- One active support worker: Wendy Worker.
- One active participant-worker assignment.
- One active hourly support item.
- One completed shift on June 1, 2026.
- One invoiced service log linked to that shift.
- One draft invoice: `DEMO-202606-0001`.

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
