# SC Single Case Notes Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development and test-driven-development for the scoped implementation below.

**Goal:** One required SC Case notes input with a short muted hint, without losing legacy notes or changing review/billing behavior.

**Architecture:** Exclude coordinator_notes from the SC ModelForm, retaining its model field and audit snapshot key. Render legacy notes only when nonempty. Reuse existing placeholder styling and keep all other form/review guards.

**Tech Stack:** Django ModelForms/templates, Django tests, local browser preview.

## Task 1: Form and Legacy Notes

Files: `coordinators/forms.py`, `templates/coordinators/sc_coordination_log_form.html`, `templates/coordinators/sc_coordination_log_detail.html`, `templates/coordinators/coordination_log_detail.html`, `coordinators/tests_single_notes.py`.

- [x] Write regression tests: create/edit expose only case_notes; placeholder is not a value; blank notes are rejected; forged coordinator_notes are ignored; edits preserve legacy content and snapshot values; identical submissions with legacy notes do not create revisions; SC/Admin details show nonempty legacy notes but omit empty sections; historical diffs retain both fields.
- [x] Run the isolated test runner with `coordinators.tests_single_notes` and confirm expected failures. Eight tests exposed nine expected failing assertions before implementation.
- [x] Remove coordinator_notes from form Meta.fields/widgets and its template field include. Set `forms.Textarea(attrs={"rows": 5, "placeholder": "Record the work completed, outcome, and any follow-up."})` for case_notes. Scope original_values to `field in self.fields` while leaving snapshot fields untouched. Wrap legacy detail output in `{% if log.coordinator_notes %}`.
- [x] Run the new tests and revision/history regressions. Review spec compliance and quality. Do not commit or deploy during this local preview iteration. 59 focused tests passed; both independent reviews found no implementation issues. Added explicit SC legacy-history and forged-legacy-field no-op coverage after review.

## Task 2: Verification and Preview

- [x] Run the full isolated SQLite suite, `git diff --check`, and migration dry run. Preserve unrelated dirty work. Full suite: 754 passed, one PostgreSQL-only contention test skipped; no migration changes or diff errors. The eight new tests were rerun after extending legacy-history coverage to SC as well as Admin.
- [x] Restart only the local 8004 resume server using its existing DB and sessions. Verify actual create/edit fields, placeholder, legacy details, and mobile layout. Do not submit real demo record changes or touch deployed data. Browser checks confirmed empty-value placeholder, typed text hiding it, no second input, preserved legacy SC/Admin details, no mobile overflow and no console errors. Temporary viewport reset.
- [x] Open the local SC preview and report results; leave production, GitHub and staging unchanged. Preview: `http://127.0.0.1:8004/sc/logs/new/`.
