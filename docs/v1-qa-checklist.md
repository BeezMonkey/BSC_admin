# V1 QA Checklist

Use this checklist before treating the local V1 build as ready for extended user trial. For a high-level release summary, see `docs/v1-trial-release-notes.md`.

For a role-by-role browser testing table, see `docs/staging-smoke-test-matrix.md`.

For a repeatable local trial data set, run:

```powershell
python manage.py migrate
python manage.py seed_demo_data
```

See `docs/local-demo-data.md` for demo credentials and suggested pages.

## Accounts and access

- Admin can log in and reach the admin dashboard.
- Worker can log in and reach the worker dashboard.
- Accountant can access invoice and export pages.
- Worker accounts cannot access admin-only participant, worker, roster, invoice, audit, or settings pages.
- Logged-out users are redirected to login for protected pages.

## Admin workflow

- Create and edit a participant.
- Create and edit a support worker.
- Assign a worker to a participant.
- Create or import support items.
- Create a one-off roster shift.
- Create recurring roster shifts.
- Publish a shift.
- Open service logs submitted by workers.
- Approve and reject service logs.
- Generate an invoice from approved logs.
- Export invoice CSV and PDF.
- Upload and download documents.
- Review audit logs for key actions.

## Worker workflow

- View assigned shifts from My Shifts.
- Open a shift detail page.
- Submit a service log for a completed shift.
- View submitted logs from My Logs.
- Open shared documents from Docs.
- Open Profile and confirm worker details display.

## Data and deployment readiness

- Run `python manage.py check`.
- Run `python manage.py test`.
- Confirm `.env` is not committed.
- Confirm `DATABASE_URL` is blank for local SQLite use.
- Review `docs/deployment-checklist.md` before any online deployment.

## Known V1 limits

- Layout is functional and intentionally plain; final visual theme can be applied later.
- Calendar-style roster views are not yet implemented.
- Email/SMS notifications are not yet implemented.
- Advanced payroll and provider-level finance workflows are not yet implemented.
