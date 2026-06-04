# Staging Smoke Test Matrix

Use this matrix for local V1 review, staging deployment smoke testing, and tester handoff. Replace `http://127.0.0.1:8000` with the staging URL when testing online.

For local seeded data and demo credentials, see `docs/local-demo-data.md`.

## Test Accounts

| Role | Local demo username | Purpose |
| --- | --- | --- |
| Admin | `admin` | Full operational workflow testing |
| Accountant | `accountant` | Invoice and export workflow testing |
| Worker | `worker` | Worker portal testing |

Do not use local demo passwords for real staff or production.

## Access And Login

| ID | Role | URL | Check | Expected result | Data change | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| A01 | Logged out | `/login/` | Open login page | Login form loads over expected host/protocol | No | On staging, URL should be HTTPS |
| A02 | Admin | `/admin-dashboard/` | Log in as admin | Admin dashboard opens | No | Confirms role redirect |
| A03 | Worker | `/sw/dashboard/` | Log in as worker | Worker dashboard opens | No | Confirms worker portal access |
| A04 | Accountant | `/invoices/` | Log in as accountant | Invoice list opens | No | Confirms finance role access |
| A05 | Worker | `/participants/` | Try admin-only URL | Access denied or redirected according to permission handling | No | Worker must not see participant admin pages |
| A06 | Logged out | `/roster/` | Open protected URL after logout | Redirected to login | No | Confirms authentication guard |

## Admin Read-Only Pages

| ID | Role | URL | Check | Expected result | Data change | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | Admin | `/admin-dashboard/` | Open dashboard | Operations summary and module cards render | No | Counts should match current test data |
| R02 | Admin | `/participants/` | Open participant list | Table, filters, actions render | No | Check AU date format where dates appear |
| R03 | Admin | `/workers/` | Open support worker list | Table, filters, actions render | No | Check status pills and action buttons align |
| R04 | Admin | `/roster/` | Open roster list | Shift rows, filters, sort links render | No | Check dates as `dd/mm/yyyy` |
| R05 | Admin | `/service-logs/` | Open service log list | Logs, status filter, invoice shortcut render | No | Check dates as `dd/mm/yyyy` |
| R06 | Admin or Accountant | `/invoices/` | Open invoice list | Invoice rows, filters, actions render | No | Check totals show two decimals |
| R07 | Admin | `/documents/` | Open documents list | Document rows and upload action render | No | Do not open private real documents in staging |
| R08 | Admin | `/settings/support-items/` | Open support items | Support item rows and filters render | No | Use test NDIS items only |
| R09 | Admin | `/audit-logs/` | Open audit logs | Audit actions and timestamps render | No | Check `dd/mm/yyyy HH:MM` |

## Admin Write Workflow

| ID | Role | URL | Check | Expected result | Data change | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| W01 | Admin | `/participants/new/` | Create test participant | Participant saves and detail page opens | Yes | Use clearly fake/anonymized details |
| W02 | Admin | `/participants/` | Edit test participant | Edited fields save correctly | Yes | Avoid real NDIS numbers |
| W03 | Admin | `/workers/new/` | Create test worker | Worker profile saves and appears in list | Yes | Use fake email/phone |
| W04 | Admin | Participant detail | Assign worker | Assignment appears on participant and worker detail | Yes | Confirm active assignment dates |
| W05 | Admin | `/roster/new/` | Create one-off shift | Shift detail opens with draft/published status | Yes | Use test participant/worker |
| W06 | Admin | `/roster/recurring/new/` | Preview recurring shifts | Preview table shows expected dates and conflicts | No | Preview alone should not create records |
| W07 | Admin | `/roster/recurring/new/` | Confirm recurring shifts | Draft shifts are created | Yes | Use short date range for staging |
| W08 | Admin | Shift detail | Publish or edit shift | Status/action updates correctly | Yes | Record shift ID for worker test |

## Worker Workflow

| ID | Role | URL | Check | Expected result | Data change | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | Worker | `/sw/dashboard/` | Open dashboard | Worker dashboard loads | No | Sidebar should fit screen |
| S02 | Worker | `/sw/shifts/` | View shifts | Needs attention/upcoming/completed groups render | No | Confirm status pills are clear |
| S03 | Worker | `/sw/shifts/<id>/` | Open assigned shift | Shift detail opens | No | Use a shift assigned to this worker |
| S04 | Worker | Shift detail | Confirm shift | Shift status becomes confirmed | Yes | Only do this on staging/test data |
| S05 | Worker | Confirmed shift | Complete service log | Service log submits and detail opens | Yes | Use test notes only |
| S06 | Worker | `/sw/logs/` | View submitted logs | New log appears | No | Check date format |
| S07 | Worker | `/sw/documents/` | View worker documents | Shared document list opens | No | Do not upload real documents |
| S08 | Worker | `/sw/profile/` | View profile | Contact and assigned participant data render | No | Check layout on desktop/mobile if possible |

## Service Log And Invoice Workflow

| ID | Role | URL | Check | Expected result | Data change | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| I01 | Admin | `/service-logs/` | Open submitted log | Detail page opens | No | Use worker-submitted test log |
| I02 | Admin | Service log detail | Approve log | Status becomes approved | Yes | Audit log should be written |
| I03 | Admin | `/service-logs/?status=approved` | Select approved logs | Bulk invoice button is visible | No | Select same participant only |
| I04 | Admin or Accountant | `/invoices/new/` | Preview invoice logs | Approved logs table appears | No | Preview should not create invoice |
| I05 | Admin or Accountant | Invoice preview | Create invoice | Invoice detail opens and log becomes invoiced | Yes | Check total and line amounts |
| I06 | Admin or Accountant | Invoice detail | Download CSV | CSV downloads and dates/totals are correct | No | Open file if needed |
| I07 | Admin or Accountant | Invoice detail | Download PDF | PDF downloads and totals are two decimals | No | Check period date format |
| I08 | Admin or Accountant | Invoice detail | Mark issued/paid or cancel | Status changes as expected | Yes | Use staging/test invoice only |

## Documents And Audit

| ID | Role | URL | Check | Expected result | Data change | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| D01 | Admin | `/documents/new/` | Upload test document | Document detail opens | Yes | Use a harmless fake file |
| D02 | Admin | Document detail | Download document | Download succeeds | No | Confirm permission-protected access |
| D03 | Worker | `/sw/documents/` | View worker-accessible documents | Only permitted documents appear | No | Worker must not see unrelated files |
| D04 | Admin | `/audit-logs/` | Review audit entries | Recent actions are listed | No | Look for service log, invoice, document actions |

## Deployment Checks

| ID | Role | Command or URL | Check | Expected result | Data change | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| C01 | Developer | `python manage.py check` | Django system check | No issues | No | Run before tester handoff |
| C02 | Developer | `python manage.py check --deploy` | Deployment warnings | No unresolved staging-critical warnings | No | HSTS may stay disabled for early staging |
| C03 | Developer | Backup tooling | Create database backup | Backup file created | No | Store outside public web root |
| C04 | Developer | Restore process | Restore backup to test target | Restored database works | Yes | Do not overwrite useful staging data without approval |

## Issue Report Format

Ask testers to report issues with:

- Test ID.
- Role used.
- Page URL.
- Steps taken.
- Expected result.
- Actual result.
- Screenshot if visual.
- Whether data was created or changed.
