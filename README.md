# Brisbane Star Care NDIS Admin System

Internal Django admin system for Brisbane Star Care NDIS operations.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Phase 0 Scope

- Django project foundation.
- Login/logout.
- UserProfile roles.
- Role-based redirect.
- Placeholder admin, worker, and invoice pages.
