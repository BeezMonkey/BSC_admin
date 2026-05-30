# Phase 12C Production Readiness Design

## Goal

Phase 12C prepares the project for future deployment without actually deploying it. The system remains local-development friendly while gaining clear environment configuration, database configuration entry points, and a deployment checklist.

## Scope

This phase includes:

- Expanded `.env.example`.
- `DATABASE_URL` parsing helper.
- Default SQLite remains unchanged.
- Optional PostgreSQL-style `DATABASE_URL` support.
- README updates for local setup and deployment preparation.
- Deployment checklist document.
- Tests for database URL parsing.

This phase does not include live server deployment, Docker, cloud setup, PostgreSQL installation, automated backups, CI/CD, or domain/SSL configuration.

## Configuration

The project continues to load `.env` via `python-dotenv`. Local development can omit `DATABASE_URL` and use SQLite. Future deployment can set a PostgreSQL URL such as:

```text
postgres://user:password@host:5432/database
```

The parser returns a Django `DATABASES["default"]` configuration.

## Deployment Checklist

The checklist records human deployment requirements:

- Set `DJANGO_SECRET_KEY`.
- Set `DJANGO_DEBUG=False`.
- Set `DJANGO_ALLOWED_HOSTS`.
- Configure production database.
- Run migrations.
- Run collectstatic.
- Back up database and media.
- Remove or rotate test accounts.
- Run `python manage.py check --deploy`.

## Tests

Tests cover:

- Missing `DATABASE_URL` returns default SQLite config.
- PostgreSQL URL parses engine, name, user, password, host, and port.
- SQLite URL parses as a file-backed SQLite config.
