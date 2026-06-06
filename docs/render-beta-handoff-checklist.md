# Render Beta Handoff Checklist

Use this checklist when creating the first Render beta environment from the GitHub `main` branch. Keep this as a private beta with test or anonymized data only.

## 1. Before You Start
- Confirm the GitHub repository is up to date: `BeezMonkey/BSC_admin`.
- Confirm the latest stable work is merged into `main`.
- Keep this document open beside Render.
- Do not upload real NDIS documents during the first beta.
- Do not use beta for official staff attendance, billing, or production records.

## 2. Create PostgreSQL
In Render:

```text
New
PostgreSQL
```

Recommended beta values:

```text
Name: bsc-admin-beta-db
Region: choose the same region as the web service
Plan: start with the lowest paid plan suitable for beta
```

After creation:
- Copy the **Internal Database URL**.
- Use that value as the web service `DATABASE_URL`.
- Do not paste database credentials into GitHub, docs, screenshots, or chat.

## 3. Create Web Service
In Render:

```text
New
Web Service
Connect GitHub repository
BeezMonkey/BSC_admin
```

Recommended beta values:

```text
Name: bsc-admin-beta
Branch: main
Runtime: Python
Region: same region as PostgreSQL
Instance type: Starter is enough for first beta testing
```

## 4. Render Commands
Use these exact command fields.

Build Command:

```text
./build.sh
```

Pre-Deploy Command:

```text
python manage.py migrate
```

Start Command:

```text
python -m gunicorn bscare_ndis.wsgi:application --bind 0.0.0.0:$PORT
```

## 5. Environment variables
Add these in the Render web service environment tab.

```text
DJANGO_SECRET_KEY=<generate-a-long-random-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-service>.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-service>.onrender.com
DATABASE_URL=<Render PostgreSQL Internal Database URL>
DJANGO_SECURE_PROXY_SSL_HEADER=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=0
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
DJANGO_SECURE_HSTS_PRELOAD=False
```

Notes:
- Render may also provide `RENDER_EXTERNAL_HOSTNAME`; the app can add it to allowed hosts automatically.
- Keep HSTS disabled for the first beta unless the domain setup is final.
- If you add a custom domain later, update `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.

## 6. First Deploy
After saving the service:
- Trigger the first deploy.
- Confirm the build runs `./build.sh`.
- Confirm static files are collected.
- Confirm the pre-deploy migration step completes.
- Confirm the app starts with Gunicorn.
- Open the `.onrender.com` URL over HTTPS.

## 7. First admin account
Create the First admin account only after the database exists and migrations have run.

Recommended options:

```text
Render Shell:
python manage.py createsuperuser --username admin --email <owner-email>
```

Then:
- Add the app role for the account:

```text
python manage.py shell -c 'from django.contrib.auth import get_user_model; from accounts.models import UserProfile; User=get_user_model(); user=User.objects.get(username="admin"); user.is_staff=True; user.is_superuser=True; user.save(); UserProfile.objects.update_or_create(user=user, defaults={"role":UserProfile.Role.ADMIN, "is_active_worker":False}); print("Admin role ready:", user.username)'
```

- Log in through the beta URL.
- Confirm the user has an admin role in the app profile data.
- Use a strong temporary password.
- Store credentials in a password manager.
- Do not reuse local demo passwords for staff beta accounts.

## 8. Test Accounts
Create only test accounts for beta:

```text
1 admin
1 accountant
2 support workers
2-3 demo participants
```

Use fake names, fake NDIS numbers, fake addresses, and fake phone numbers until backup and privacy handling are confirmed.

Optional beta seed command after the first admin account is ready:

```text
python manage.py seed_beta_test_data --password <temporary-test-password>
```

This command creates safe fake trial data and does not change the owner `admin` account.

## 9. Smoke test
Run this Smoke test before inviting staff:

- Root URL redirects to the login page.
- Health check opens at `/health/`.
- Login page opens over HTTPS.
- Admin login works.
- Worker login works.
- Logged-out users are redirected to login.
- Worker cannot open admin-only pages.
- Admin can create a participant.
- Admin can create a support worker.
- Admin can assign worker to participant.
- Admin can create and publish a shift.
- Worker can confirm the shift.
- Worker can submit a service log.
- Admin can approve the service log.
- Admin can create an invoice from approved logs.
- Invoice CSV downloads.
- Invoice PDF downloads.
- Document upload/download is tested with a fake file only.
- Audit logs record the major actions.

## 10. Known Beta Limits
- Uploaded media still needs a durable storage and backup decision.
- Do not rely on Render instance storage for important uploaded documents.
- HSTS is intentionally off for early beta.
- Staff feedback should focus on workflow, layout, wording, and missing fields.
- Any serious business use needs a backup/restore test first.

## 11. If Deploy Fails
Check in this order:

- Build log: dependency install or `collectstatic` error.
- Pre-deploy log: migration/database error.
- Runtime log: Gunicorn or environment variable error.
- `DJANGO_ALLOWED_HOSTS`: missing `.onrender.com` hostname.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: missing HTTPS origin.
- `DATABASE_URL`: wrong database URL or external URL used by mistake.

If a deploy breaks beta:
- Do not enter real data.
- Roll back to the previous successful Render deploy.
- Fix locally, push a new branch, merge through GitHub, and redeploy.
