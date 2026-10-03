# SC Service Duration Implementation Plan

> **For agentic workers:** Use test-driven-development for this tightly coupled form/model/template change, then independent spec and quality review.

**Goal:** SC logs accept service duration in hours/minutes instead of start/end/break and manually duplicated decimal hours.

**Architecture:** Keep actual_hours as the invoice quantity source and derive it server-side with Decimal/ROUND_HALF_UP to two decimal places. Make existing clock fields nullable, never fabricate clock values, preserve legacy clock values/notes/history, and leave SW/invoice code unchanged. No JavaScript dependency for conversion. Duration is 1..1440 minutes, minutes 0..59, hours 0..24. Preserve existing decimal quantity for unchanged duration on legacy edits to avoid rounding historical imported data.

**Tech Stack:** Django ModelForm, nullable field migration, scoped CSS, Django/browser tests.

## Approved Scope

User confirmed duration-only SC workflow on 2026-10-04. Participant, service date, coordination type and required Case notes remain. Existing assignment/ownership/review reset/stale token/invoice locks stay intact. Existing start/end/break information is shown only when present, labelled previously recorded time; no new phantom times. Legacy fields and snapshots remain stored. Lists and invoice quantities continue using decimal hours; details show human-readable duration. No commit/push/deployment during local preview.

## 1. Regression Tests

- [x] Add `coordinators/tests_duration.py`: one minute/30/75/80/1440-minute conversion, invalid/missing/fractional/out-of-range parts, forged actual_hours/times ignored, new logs without clocks, edit prefill/no-op/unchanged legacy precision, duration-only edit resubmission/history, legacy clocks/notes preservation, invoice decimal quantity, SC/Admin display and absence of obsolete inputs.
- [x] Update SC POST fixtures in existing coordinator tests to duration_hours/duration_minutes; replace obsolete clock validation tests with duration validation, keeping model fixtures and historic snapshot tests intact. Run RED before implementation. Confirmed 27 expected failing assertions in 11 tests before implementation.

## 2. Implementation

- [x] `coordinators/models.py` and `migrations/0004_optional_log_times.py`: start/end `TimeField(null=True, blank=True)`; reusable `duration_parts` and `service_duration_display` properties derived from actual_hours. No data migration.
- [x] `coordinators/forms.py`: integer duration fields; exclude start/end/break/actual_hours from form fields; calculate cleaned actual_hours with `(Decimal(total_minutes) / Decimal(60)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`; save computed quantity server-side; compare derived actual_hours in no-op detection. Keep revision guards/reason logic unchanged.
- [x] SC form: Service duration fieldset with labelled Hours/Minutes number controls; only date picker remains. Add `static/css/sc_log_form.css` scoped layout. SC/Admin details show duration and conditional previously-recorded time/break details. Keep decimal Hours in lists/invoice previews.
- [x] Run focused tests, independent spec and quality review; address findings. Coordinator/invoice suite: 260 passed, 1 PostgreSQL-only skip. Independent spec and quality reviews found no actionable issues. Duration tests rerun after CSS polish: 11 passed.

## 3. Verify and Preview

- [x] Full isolated SQLite suite: 765 passed, 1 PostgreSQL-only skip. Django check passed; makemigrations --check --dry-run reported no changes; diff whitespace check passed. PostgreSQL contention remains unverified locally.
- [x] Stop only local8004 preview server, back up its existing demo DB, apply nullable migration using isolated preview settings, assert log/history data is unchanged, restart same DB/session (no seed/reset). Compared all fields for 5 logs, 6 history entries, 1 invoice and 1 invoice line before/after: identical.
- [x] Browser verified desktop and 390px mobile create form, invalid duration errors, existing edit duration prefill, and Admin legacy time/notes/history. No horizontal overflow or observed console warnings/errors. Used separate temporary QA tabs; no existing demo record submitted. No staging/production writes.
