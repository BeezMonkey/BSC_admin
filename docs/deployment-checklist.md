# Deployment Readiness Checklist

This project is still intended to run locally until a separate deployment phase is approved. Use this checklist before any future production deployment.

Read the broader readiness review first:

```text
docs/pre-deployment-review.md
docs/render-beta-deployment.md
docs/staging-deployment-plan.md
docs/staging-runbook.md
```

## Environment

- Set `DJANGO_SECRET_KEY` to a strong unique value.
- Set `DJANGO_DEBUG=False`.
- Set `DJANGO_ALLOWED_HOSTS` to the real domain names and server hostnames.
- Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the real HTTPS origins.
- On Render, confirm `RENDER_EXTERNAL_HOSTNAME` is present or include the `.onrender.com` hostname in `DJANGO_ALLOWED_HOSTS`.
- Confirm the business timezone remains `Australia/Brisbane`.
- Enable HTTPS settings only after SSL and proxy behavior are confirmed.
- Keep `.env` out of Git.
- Rotate or remove local demo/test accounts before go-live.

## Database

- Leave `DATABASE_URL` blank for local SQLite.
- Set `DATABASE_URL` for production database access.
- Confirm the production database driver is installed and tested.
- PostgreSQL example:

```text
DATABASE_URL=postgres://bsc_user:password@db-host:5432/bsc_admin
```

- Run `python manage.py migrate` during deployment.
- Confirm database backups are automated and restore-tested.

## Static And Media

- Run `python manage.py collectstatic` for production static assets.
- Confirm collected static files are served from `STATIC_ROOT`.
- Confirm WhiteNoise serves static assets in the target environment.
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
- Complete `docs/v1-qa-checklist.md` in staging before go-live.
