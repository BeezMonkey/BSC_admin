# Brisbane Star Care NDIS Admin System

Internal Django admin system for Brisbane Star Care NDIS operations.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Environment

Local development uses SQLite by default. Leave `DATABASE_URL` blank unless you are preparing a production-like database.

Common `.env` values:

```text
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=
```

For future PostgreSQL deployment:

```text
DATABASE_URL=postgres://bsc_user:password@db-host:5432/bsc_admin
```

## Current Functional Scope

- Role-based login and dashboards.
- Participant and support worker management.
- Participant-worker assignment.
- Support item management.
- Basic and recurring shift scheduling.
- Worker shift confirmation and service log submission.
- Admin service log approval/rejection.
- Invoice generation, CSV export, and simple PDF export.
- Document upload/download with basic permissions.
- Audit logs for key business actions.

## Deployment Preparation

This repository is not deployed by Phase 12C. It remains a local development project with deployment-ready configuration entry points.

Before any future production deployment, review:

```text
docs/deployment-checklist.md
```

For V1 review and local browser testing, review:

```text
docs/v1-qa-checklist.md
docs/v1-completion-summary.md
```

Useful checks:

```powershell
python manage.py check
python manage.py test
python manage.py check --deploy
```
