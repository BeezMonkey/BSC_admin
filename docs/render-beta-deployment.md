# Render Beta Deployment

Use this guide for the first private Render beta deployment. This is not a production go-live plan. Use test or anonymized data only.

## Purpose
- Prove the Django app can run online from GitHub.
- Let a small trusted group test the workflow.
- Keep local development, pull requests, and GitHub as the normal source of truth.

## Recommended Beta Shape
- Render web service connected to the GitHub `main` branch.
- Render PostgreSQL database using the internal database URL.
- Test accounts only.
- No real NDIS documents or sensitive participant records during the first beta.

## Render Service Commands

Build command:

```text
./build.sh
```

Pre-deploy command:

```text
python manage.py migrate
```

Start command:

```text
python -m gunicorn bscare_ndis.wsgi:application --bind 0.0.0.0:$PORT
```

Render web services must bind to the platform-provided port.

## Required Environment Variables

```text
DJANGO_SECRET_KEY=<generate-a-long-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-service>.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-service>.onrender.com
DATABASE_URL=<render-postgres-internal-url>
DJANGO_SECURE_PROXY_SSL_HEADER=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=0
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
DJANGO_SECURE_HSTS_PRELOAD=False
```

Notes:
- Render also provides `RENDER_EXTERNAL_HOSTNAME`; the app can add it to `ALLOWED_HOSTS` automatically.
- Keep HSTS disabled for the first beta until the domain and HTTPS setup are final.
- Store environment values in Render, not in GitHub or `.env`.

## Database
- Use Render PostgreSQL for beta.
- Use the internal database URL when the web service and database are in the same Render region.
- Run migrations through the pre-deploy command or Render Shell before inviting testers.
- Confirm backups before any real data is entered.

## Static And Media Files
- Static files are collected by `build.sh`.
- WhiteNoise serves collected static assets from the app.
- Uploaded media files still need a persistence decision before serious staff trial.
- Do not rely on ephemeral instance storage for important uploaded documents.

## First Beta Smoke Test
- Login page opens over HTTPS.
- Admin login works.
- Worker login works.
- Logged-out users are redirected to login.
- Worker cannot open admin-only pages.
- Admin can create participant and support worker records.
- Admin can create and publish a shift.
- Worker can confirm a shift and submit a service log.
- Admin can approve a service log.
- Admin can create an invoice from approved logs.
- Invoice CSV/PDF downloads work.
- Document upload/download behavior is reviewed.
- Audit logs record key actions.

## Go / No-Go
Go only if:
- `python manage.py check` passes.
- `python manage.py check --deploy` has no staging-critical warnings.
- Static files load online.
- Database migrations complete.
- Test accounts can complete the smoke test.
- Backup and media-file responsibilities are clear.

No-go if:
- Real participant or NDIS data is required before backup/media handling is solved.
- Staff will rely on the beta for official attendance or billing.
- Login, permissions, service logs, or invoice generation fail the smoke test.
