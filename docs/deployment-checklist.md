# Deployment Readiness Checklist

This project is still intended to run locally until a separate deployment phase is approved. Use this checklist before any future production deployment.

Read the broader readiness review first:

```text
docs/pre-deployment-review.md
docs/render-beta-deployment.md
docs/staging-deployment-plan.md
docs/staging-runbook.md
docs/render-storage-configuration.md
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
- For local development, uploaded documents live in `MEDIA_ROOT` and should be backed up if needed.
- For Render document uploads, configure private SFTP storage before accepting real worker documents. Use `docs/render-storage-configuration.md` as the source of truth:
  - `DOCUMENT_STORAGE_BACKEND=sftp`
  - `DOCUMENT_SFTP_HOST=ftp.duratechequip.com`
  - `DOCUMENT_SFTP_PORT=22`
  - `DOCUMENT_SFTP_USERNAME=duratech`
  - `DOCUMENT_SFTP_PRIVATE_KEY=<complete private key including BEGIN/END lines>`
  - `DOCUMENT_SFTP_KEY_PASSPHRASE=<private key passphrase>`
  - `DOCUMENT_SFTP_ROOT=/home4/duratech/bsc_private_uploads`
  - `DOCUMENT_SFTP_TIMEOUT=10`
- Keep the SFTP key restricted to the hosting account and store uploaded documents under `/home4/duratech/bsc_private_uploads`.
- Rotate the SFTP key passphrase before uploading real compliance or service log documents.
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
