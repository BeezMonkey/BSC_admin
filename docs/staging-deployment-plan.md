# Staging Deployment Plan

This plan describes how to prepare a future staging deployment for the Brisbane Star Care NDIS admin system. Staging means a private test server used before production. It is not the live production system.

For an executable deployment checklist, use:

```text
docs/staging-runbook.md
```

## Goal

- Test the application outside the local laptop.
- Confirm deployment steps before any real go-live decision.
- Check database, static files, uploaded documents, login, permissions, and exports in a server-like environment.
- Keep demo/test data separate from real production data.

## Recommended Order

1. Continue local V1 trial until the main workflows are stable.
2. Create a staging environment.
3. Run a staging deployment using test data only.
4. Complete browser QA on staging.
5. Fix any staging-only issues.
6. Decide whether production deployment is needed.

## Deployment Options

### Managed Platform

Examples: Render, Railway, Fly.io, PythonAnywhere, or another managed Django-friendly platform.

Pros:

- Faster setup.
- Often includes HTTPS and environment variable management.
- Easier for a small team to maintain.

Cons:

- Monthly cost can increase with database and storage.
- Some platforms need extra setup for persistent uploaded files.
- Less server-level control.

### VPS

Examples: a Linux VPS from providers such as DigitalOcean, Vultr, Linode, AWS Lightsail, or similar.

Pros:

- More control over server, database, backups, and file storage.
- Can be cost effective once configured.

Cons:

- More maintenance responsibility.
- Requires web server, process manager, SSL, firewall, backup, and update setup.

## Suggested Staging Stack

For the first staging attempt, prefer the simplest reliable setup:

- Django application running with a production WSGI server.
- PostgreSQL staging database.
- HTTPS enabled.
- Static files served from collected `staticfiles/`.
- Uploaded documents stored in a persistent media location.
- Scheduled backup for database and media.

The exact platform can be chosen later. This document keeps the steps platform-neutral.

## Required Environment Values

Create a staging `.env` from `.env.example` and set values similar to:

```text
DJANGO_SECRET_KEY=replace-with-staging-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=staging.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.example.com

DATABASE_URL=postgres://bsc_staging_user:password@db-host:5432/bsc_staging

DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=0
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
DJANGO_SECURE_HSTS_PRELOAD=False
DJANGO_SECURE_PROXY_SSL_HEADER=True
```

Keep HSTS at `0` for staging unless the domain and HTTPS setup are final. HSTS can be difficult to reverse if enabled too early.

## Dependencies To Confirm

Before staging deployment, confirm these deployment dependencies:

- Production WSGI server package, such as Gunicorn on Linux.
- PostgreSQL driver if PostgreSQL is used.
- Platform-specific static file serving approach.
- Platform-specific persistent media storage approach.
- Backup tooling for database and media.

Do not add these dependencies blindly until the target platform is selected.

## Staging Deployment Steps

1. Create the staging server or platform app.
2. Create the staging PostgreSQL database.
3. Add environment variables from the staging `.env` values.
4. Install Python dependencies.
5. Install any platform-specific deployment dependencies.
6. Run `python manage.py migrate`.
7. Run `python manage.py collectstatic --noinput`.
8. Create a staging superuser.
9. Load demo data only if needed.
10. Start the Django app through the platform process manager.
11. Open the staging URL and complete smoke testing.

## Staging Smoke Test

Use test accounts only.

- Login page opens over HTTPS.
- Admin login works.
- Worker login works.
- Admin cannot access with invalid credentials.
- Worker cannot access admin pages.
- Admin dashboard opens.
- Participant list, detail, create, and edit pages work.
- Worker list, detail, create, and edit pages work.
- Roster pages load and show expected shifts.
- Worker shift pages load.
- Worker service log submission works.
- Admin service log review works.
- Invoice list and invoice detail pages work.
- CSV export works.
- PDF export works.
- Document upload and download work.
- Audit log page records key actions.
- Logout works.

## Data Rules

- Do not use real participant data in staging unless explicit privacy controls and approval are in place.
- Do not use production passwords in staging.
- Do not reuse local demo passwords for real users.
- Keep staging database and media separate from production.
- If real-like test data is needed, anonymize names, phone numbers, emails, addresses, notes, and document files.

## Backup Checks

Before staging is considered stable:

- Confirm database backup can be created.
- Confirm database backup can be restored.
- Confirm uploaded media files are included in backup.
- Confirm backup files are not publicly accessible.

## Security Checks

Run:

```powershell
python manage.py check
python manage.py check --deploy
```

Expected staging result:

- `check` should pass.
- `check --deploy` should have no unresolved critical production warnings, except settings intentionally left relaxed for staging such as HSTS.

## Decision Before Production

Only consider production after staging confirms:

- Hosting is stable.
- Database and media backups work.
- HTTPS and host settings are correct.
- Browser QA passes.
- Demo accounts are removed or rotated.
- Real admin accounts are created.
- Access rules are re-tested.
- Business users accept the workflow.

## Recommendation

Use staging as the next deployment-related milestone. Avoid direct production deployment from the local environment.
