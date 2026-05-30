# Deployment Readiness Checklist

This project is still intended to run locally until a separate deployment phase is approved. Use this checklist before any future production deployment.

## Environment

- Set `DJANGO_SECRET_KEY` to a strong unique value.
- Set `DJANGO_DEBUG=False`.
- Set `DJANGO_ALLOWED_HOSTS` to the real domain names and server hostnames.
- Keep `.env` out of Git.
- Rotate or remove local demo/test accounts before go-live.

## Database

- Leave `DATABASE_URL` blank for local SQLite.
- Set `DATABASE_URL` for production database access.
- PostgreSQL example:

```text
DATABASE_URL=postgres://bsc_user:password@db-host:5432/bsc_admin
```

- Run `python manage.py migrate` during deployment.
- Confirm database backups are automated and restore-tested.

## Static And Media

- Run `python manage.py collectstatic` for production static assets.
- Back up `MEDIA_ROOT` because uploaded documents live there.
- Confirm document downloads are protected by application permissions.

## Security Checks

- Run:

```powershell
python manage.py check --deploy
```

- Review warnings before go-live. Some checks may need environment-specific server settings.

## Operational Checks

- Confirm admin access is limited to trusted staff.
- Confirm worker accounts can only access `/sw/*` pages.
- Confirm audit logs are being written for key actions.
- Confirm invoice CSV/PDF export works in the target environment.
