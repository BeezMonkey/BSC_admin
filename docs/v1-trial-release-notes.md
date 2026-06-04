# V1 Trial Release Notes

This document summarizes the current local V1 trial build for the Brisbane Star Care NDIS admin system.

## Status

V1 is ready for local trial and feedback. It is not yet a production deployment.

Use it to test core admin, worker, and finance workflows with local demo data.

## Prepare Local Trial Data

Run:

```powershell
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/login/
```

Demo credentials:

```text
admin / BscTest123!
worker / BscTest123!
accountant / BscTest123!
```

These credentials are for local trial only and must not be used in production.

## Included In V1

- Role-based login and redirects.
- Admin dashboard and worker dashboard.
- Participant records.
- Support worker records.
- Participant-worker assignments.
- Support item records.
- One-off and recurring shift scheduling.
- Worker shift views and shift confirmation.
- Worker service log submission.
- Admin service log review.
- Invoice generation from approved service logs.
- Invoice CSV export and simple PDF export.
- Document upload and download.
- Worker document access.
- Audit logs for key business actions.
- Local demo data command.
- V1 trial UI polish, including clearer list actions, empty states, and detail-page back links.

## Seeded Demo Data

The local demo command prepares:

- Admin, worker, and accountant accounts.
- Participants: Ava Nguyen and Ben Taylor.
- Worker: Wendy Worker.
- Two participant-worker assignments.
- One hourly support item.
- Two completed shifts.
- Two invoiced service logs.
- Two draft invoices:
  - `DEMO-202606-0001`
  - `DEMO-202606-0002`

## Suggested Trial Routes

Admin:

```text
http://127.0.0.1:8000/admin-dashboard/
http://127.0.0.1:8000/participants/
http://127.0.0.1:8000/workers/
http://127.0.0.1:8000/roster/
http://127.0.0.1:8000/service-logs/
http://127.0.0.1:8000/invoices/
http://127.0.0.1:8000/documents/
http://127.0.0.1:8000/settings/support-items/
http://127.0.0.1:8000/audit-logs/
```

Worker:

```text
http://127.0.0.1:8000/sw/dashboard/
http://127.0.0.1:8000/sw/shifts/
http://127.0.0.1:8000/sw/logs/
http://127.0.0.1:8000/sw/documents/
http://127.0.0.1:8000/sw/profile/
```

Accountant:

```text
http://127.0.0.1:8000/invoices/
http://127.0.0.1:8000/exports/
```

## Trial Checklist

Use `docs/v1-qa-checklist.md` for a more detailed checklist. At minimum:

For structured feedback, use `docs/trial-feedback-template.md`.

- Log in as admin, worker, and accountant.
- Confirm each role lands on the correct dashboard.
- Confirm worker cannot open admin-only pages.
- Confirm admin can view participants, workers, roster, logs, invoices, documents, support items, and audit logs.
- Confirm worker can view shifts, logs, documents, and profile.
- Confirm accountant can view invoices and exports.
- Confirm seeded records display correctly.
- Confirm invoice totals display with two decimal places.

## Known V1 Limits

- This is still local-only and not deployed online.
- Final branded visual design and purchased template integration are not included yet.
- Calendar-style roster views are not included yet.
- Email and SMS notifications are not included yet.
- Advanced reporting dashboards are not included yet.
- Payroll integrations are not included yet.
- External NDIS API integrations are not included yet.
- Production backup, monitoring, and hosting setup are not included yet.

## Verification Commands

Run:

```powershell
python manage.py check
python manage.py test accounts core documents invoices participants scheduling service_logs workers -v 1
```

Before future production deployment, also review:

```text
docs/deployment-checklist.md
```
