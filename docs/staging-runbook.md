# Staging Deployment Runbook

Use this runbook when preparing a private staging deployment for user trial. Staging should use test or anonymized data only.

## 1. Prepare The Target

- Choose the staging host or managed platform.
- Confirm the staging URL, for example `https://staging.example.com`.
- Confirm where environment variables are stored.
- Confirm where uploaded media files will persist.
- Confirm how database backups will be created and restored.

Do not use the production domain or real participant records for the first staging run.

## 2. Prepare Environment Values

Create staging values from `.env.example`.

Minimum staging values:

```text
DJANGO_SECRET_KEY=replace-with-long-random-staging-secret
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

Notes:

- Keep `DJANGO_SECURE_HSTS_SECONDS=0` for early staging unless the domain and HTTPS configuration are final.
- Keep the business timezone as `Australia/Brisbane`.
- Keep `USE_TZ=True` in Django settings.
- Never commit the real staging `.env`.

## 3. Install And Configure

Run the equivalent steps for the chosen platform:

```powershell
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
```

If the platform uses PostgreSQL, confirm the required database driver is installed before migration.

## 4. Create Staging Users

Create only test accounts.

Recommended staging users:

- One admin user.
- One accountant user.
- Two worker users.

After accounts are created:

- Assign roles through the app profile records or admin tooling.
- Use strong temporary passwords.
- Store credentials in a secure password manager.
- Do not reuse local demo passwords for real staff.

## 5. Load Test Data

For the first staging deployment, choose one:

- Use no seed data and create records manually.
- Use demo data only if it is clearly marked as demo data.
- Use anonymized real-like data only after privacy approval.

If using demo data:

```powershell
python manage.py seed_demo_data
```

Before inviting testers, confirm there is no real participant, worker, address, phone, email, NDIS number, note, or uploaded document in staging.

## 6. Smoke Test After Deploy

Run these tests in the browser against the staging URL:

- Login page opens over HTTPS.
- Admin login works.
- Worker login works.
- Accountant access works for invoices.
- Logged-out users are redirected to login.
- Worker cannot open admin-only pages.
- Admin dashboard opens.
- Participants list/detail/create/edit work.
- Support Workers list/detail/create/edit work.
- Roster list/detail/create/edit work.
- Recurring shift preview and create work.
- Worker My Shifts opens.
- Worker can confirm a shift.
- Worker can submit a service log.
- Admin can approve and reject service logs.
- Approved service logs can be converted to invoice.
- Invoice detail opens.
- Invoice CSV downloads.
- Invoice PDF downloads.
- Document upload and download work.
- Audit Logs record key actions.
- Logout works.

Record any failures before inviting more testers.

## 7. Deployment Checks

Run:

```powershell
python manage.py check
python manage.py check --deploy
```

Expected:

- `check` should pass.
- `check --deploy` should have no unresolved staging-critical warnings.
- HSTS warnings can remain if HSTS is intentionally disabled for staging.

## 8. Backup And Restore Check

Before staging is considered usable:

- Create a database backup.
- Restore that backup into a separate test database or reset staging environment.
- Confirm uploaded media backup includes document files.
- Confirm backup files are not publicly accessible.
- Confirm who is responsible for monitoring backups.

## 9. Tester Handoff

Before testers use staging:

- Share the staging URL.
- Share test accounts securely.
- Explain that staging data is test data only.
- Ask testers not to upload real NDIS documents.
- Ask testers to report page URL, account role, steps taken, and screenshot for each issue.

## 10. Go/No-Go Review

After smoke testing:

- Review test results.
- Review backup results.
- Review security warnings.
- Review whether any real data was accidentally entered.
- Decide whether to fix staging issues, continue local trial, or prepare production planning.

Production deployment should not start until staging passes the agreed smoke test and backup checks.
