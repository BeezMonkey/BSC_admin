# Pre-Deployment Readiness Review

This review records the current deployment status of the Brisbane Star Care NDIS admin system. The system is ready for local V1 trial and feedback. It is not yet ready for production use until the items below are completed and tested.

## Current Status

- Local Django app is working with role-based admin and worker access.
- Local SQLite remains the default database for development and trial.
- `.env` configuration is supported.
- `DATABASE_URL` can point to SQLite or PostgreSQL-style connection strings.
- Static files have a `collectstatic` target through `STATIC_ROOT`.
- Uploaded documents are stored in local `MEDIA_ROOT`.
- Deployment has not been performed.

## Production Blockers

These items must be decided and completed before any real online use:

- Choose hosting target, domain, and SSL approach.
- Choose production database service and backup policy.
- Add and test the required PostgreSQL driver if PostgreSQL is used.
- Decide where uploaded documents will live and how they will be backed up.
- Replace local/demo credentials with real accounts.
- Remove or rotate demo users and test passwords.
- Set `DJANGO_DEBUG=False`.
- Set a unique production `DJANGO_SECRET_KEY`.
- Set real `DJANGO_ALLOWED_HOSTS`.
- Set `DJANGO_CSRF_TRUSTED_ORIGINS` for the HTTPS domain.
- Enable HTTPS cookie and redirect settings only after SSL/proxy behavior is confirmed.
- Run migrations and `collectstatic` during deployment.
- Run full browser testing in a staging environment before production.

## Environment Settings

Local development can keep:

```text
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=
```

Future production should use values similar to:

```text
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
DATABASE_URL=postgres://bsc_user:password@db-host:5432/bsc_admin
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
```

If the app is behind a trusted HTTPS proxy, `DJANGO_SECURE_PROXY_SSL_HEADER=True` can be used after the proxy configuration is verified.

## Static And Media

- Run `python manage.py collectstatic` in the deployment environment.
- `STATIC_ROOT` outputs collected static files to `staticfiles/`.
- Uploaded documents use `MEDIA_ROOT`, which is local `media/` by default.
- Production media needs backup and access-control review.

## Suggested Staging Sequence

1. Create a staging environment separate from the local machine.
2. Copy `.env.example` to a staging `.env` and fill staging values.
3. Install dependencies and any required production database driver.
4. Run `python manage.py migrate`.
5. Run `python manage.py collectstatic`.
6. Create staging admin and worker accounts.
7. Run `python manage.py check` and `python manage.py check --deploy`.
8. Complete the V1 QA checklist in the browser.
9. Confirm backups and restore process.
10. Only then decide whether to prepare production deployment.

## Known Risks

- Current demo data is not real operational data.
- Current document storage is local filesystem based.
- Production database driver and hosting stack are not finalized.
- `check --deploy` will continue to warn until production HTTPS, secret, debug, host, and cookie settings are actually configured.
- Permission behavior should be re-tested after any future UI or workflow changes.

## Recommendation

Continue local trial and feedback first. The next deployment-related step should be a staging deployment, not direct production deployment.
