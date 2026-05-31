# Phase 20 Pre-Deployment Readiness Review Design

## Purpose

Phase 20 reviews whether the V1 local trial system is ready to move toward a staging or production deployment. This phase does not deploy the system, change hosting, connect a production database, or change business workflows.

## Scope

- Add a pre-deployment readiness review document.
- Update deployment checklist guidance.
- Expose environment-driven security settings for a future HTTPS deployment.
- Add `STATIC_ROOT` so `collectstatic` has a clear output location.
- Keep local development defaults unchanged.

## Out Of Scope

- Live server setup.
- Domain, DNS, or SSL certificate setup.
- Production database creation.
- Production media storage setup.
- CI/CD pipeline setup.
- UI or business workflow changes.

## Readiness Notes

The project is ready for continued local V1 trial. It is not yet production-ready until hosting, database, media storage, HTTPS, backup, and account cleanup decisions are completed and tested in a staging environment.

## Verification

- Run Django system checks.
- Run Django deployment checks and document expected production warnings.
- Run the existing test suite because settings changed.
