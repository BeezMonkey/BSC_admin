# SC Revision Reason Picker Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to complete the scoped tasks below.

**Goal:** Preview an SC edit form with a required reason selection and optional details, required only for Other.

**Architecture:** Reuse the existing history reason/details fields. Keep all edit permissions, review resets, signed tokens, invoice guards, and SW behavior unchanged. Client-side label/required updates supplement server-side validation.

**Tech Stack:** Django forms/templates, scoped vanilla JavaScript, Django tests, Playwright.

## Task 1: Regression Tests

- [x] Update `coordinators/tests_revisions.py` payloads to `revision_reason=other` and `revision_details=Corrected the provider outcome.`; assert both are recorded separately.
- [x] Add tests for all four preset reasons with empty details, empty/invalid selection, Other with whitespace details, details trimming/length/escaping, unselected GET, and invalid form retaining the selection and notes.
- [x] Run the isolated SQLite test runner with `coordinators.tests_revisions`; confirm failures on the missing choices/details behavior (15 expected assertions failed).

## Task 2: Implementation

- [x] In `coordinators/forms.py`, replace the free-text reason with `forms.ChoiceField` (blank placeholder plus five choices). Add `revision_details = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={"rows": 2}))`. Set the details field's `required` and label from the submitted reason in `__init__`, reusing Django's whitespace-aware server validation.
- [x] In `coordinators/views.py`, record `reason=dict(form.fields["revision_reason"].choices)[form.cleaned_data["revision_reason"]]` and `details=form.cleaned_data["revision_details"]` through the existing atomic history writer.
- [x] In `templates/coordinators/sc_coordination_log_form.html`, render details after reason and load the new `static/js/sc_log_revision.js` only when editing.
- [x] The scoped script updates the details label, `required`, and `aria-required` on reason change; it never clears entered details or bypasses server validation.
- [x] Rerun targeted tests and the complete isolated suite; run Django check, migration dry run, and whitespace diff check. Targeted: 34 passed. Full suite: 729 passed, 1 PostgreSQL-only contention test skipped. System checks, migration dry run, and whitespace check passed.

## Task 3: Local Preview

- [x] Restart only the existing temporary SC revision demo server on 127.0.0.1:8004. Do not access deployed databases or push code.
- [x] Verify actual form behavior and history in Playwright, including Other validation without JavaScript, approval reset, invoiced lock, and 1440/390/320px layouts. Desktop/mobile screenshots inspected; no overflow or JavaScript errors.
- [x] Open the SC edit page locally and report the preview URL and its local-only status.

Independent read-only review found no actionable issues and reran all 34 revision tests.
