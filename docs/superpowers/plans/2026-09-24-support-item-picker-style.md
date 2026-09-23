# Support Item Picker Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Replace dense native support item menus with the approved compact searchable grouped presentation on Admin scheduling and Support Worker Unscheduled Service forms, without changing submitted values or business logic.

**Architecture:** Keep Django's existing \`ModelChoiceField\` and native \`<select>\` as the form source of truth. A presentation-only \`SupportItemSelect\` adds an activation attribute and each option's existing category; a shared template, scoped CSS, and progressive-enhancement JavaScript render the searchable grouped interface while synchronizing the original select.

**Tech Stack:** Django forms/templates/tests, vanilla JavaScript, existing CSS design system.

---

### Task 1: Lock The Django Field Contract

**Files:**
- Create: \`scheduling/tests_support_item_picker.py\`
- Create: \`service_logs/tests_support_item_picker.py\`
- Create: \`scheduling/widgets.py\`
- Modify: \`scheduling/forms.py\`
- Modify: \`service_logs/forms.py\`

- [ ] **Step 1: Write failing form and widget tests**

Add tests that create active categorized support items and assert:

\`\`\`python
field = ShiftForm().fields["support_item"]
self.assertEqual(list(field.queryset), [self.weekday_item, self.saturday_item])
self.assertEqual(field.widget.attrs["data-support-item-picker"], "")
html = field.widget.render("support_item", self.weekday_item.pk, choices=field.choices)
self.assertIn('value="%s"' % self.weekday_item.pk, html)
self.assertIn('data-category="Assistance with self-care activities"', html)
self.assertIn(str(self.weekday_item), html)
\`\`\`

Repeat the activation assertion for \`RecurringShiftForm\` and \`UnscheduledServiceLogForm\`. Assert inactive items remain absent. Instantiate \`SupportCoordinationInvoiceForm\` and assert its support item widget does not contain \`data-support-item-picker\`.

- [ ] **Step 2: Run tests and verify the expected failure**

Run:

\`\`\`powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py test scheduling.tests_support_item_picker service_logs.tests_support_item_picker
\`\`\`

Expected: FAIL because the picker widget and activation attribute do not exist.

- [ ] **Step 3: Implement the presentation-only widget**

Create \`SupportItemSelect(forms.Select)\` in \`scheduling/widgets.py\`. Its constructor must add \`data-support-item-picker=""\`. Override \`create_option()\` to read \`value.instance.category\` from Django's \`ModelChoiceIteratorValue\` and add that existing text as \`data-category\`; use \`Other support items\` only when the category is blank. Do not modify option labels or values.

Attach the widget only to:

\`\`\`python
ShiftForm.Meta.widgets["support_item"]
RecurringShiftForm.support_item
UnscheduledServiceLogForm.Meta.widgets["support_item"]
\`\`\`

Keep every existing queryset and empty label assignment intact.

- [ ] **Step 4: Run tests and verify they pass**

Run the Task 1 test command again.

Expected: PASS with unchanged option IDs, exact \`SupportItem.__str__()\` labels, active-item filtering, and invoice exclusion.

- [ ] **Step 5: Commit the field contract**

\`\`\`powershell
git add scheduling/widgets.py scheduling/forms.py service_logs/forms.py scheduling/tests_support_item_picker.py service_logs/tests_support_item_picker.py
git commit -m "test: lock support item picker contract"
\`\`\`

### Task 2: Add The Shared Progressive-Enhancement UI

**Files:**
- Create: \`templates/scheduling/partials/support_item_picker_field.html\`
- Create: \`static/js/support_item_picker.js\`
- Modify: \`static/css/app.css\`
- Modify: \`templates/scheduling/partials/shift_form_fields.html\`
- Modify: \`templates/scheduling/recurring_shift_form.html\`
- Modify: \`templates/service_logs/worker_service_log_form.html\`
- Modify: \`templates/scheduling/shift_form.html\`
- Modify: \`templates/scheduling/roster_planner.html\`

- [ ] **Step 1: Write failing template activation tests**

Extend the picker tests to render the Admin shift form, recurring shift form, roster planner, and Support Worker Unscheduled Service page. Assert in-scope pages contain:

\`\`\`python
self.assertContains(response, 'data-support-item-picker')
self.assertContains(response, 'js/support_item_picker.js')
\`\`\`

Assert Support Coordination invoice form HTML does not contain either marker.

- [ ] **Step 2: Run the focused tests and verify the expected failure**

Run the Task 1 test command.

Expected: FAIL because the shared partial and script references are absent.

- [ ] **Step 3: Add the shared field partial**

Create a field wrapper with an explicit \`<label for="{{ field.id_for_label }}">\`, the unchanged \`{{ field }}\`, and the existing field error rendering. Replace only the in-scope support item field includes with this partial.

- [ ] **Step 4: Add the progressive-enhancement script**

Implement \`static/js/support_item_picker.js\` to:

- initialize only \`select[data-support-item-picker]\` elements;
- leave the native select present and hide it only after successful initialization;
- copy exact option text into trigger and option rows;
- group rows by \`data-category\` without reordering them;
- filter client-side against exact existing label text;
- synchronize selection to the native select and dispatch \`change\`;
- preserve bound selections;
- close on outside click or Escape;
- support Arrow Up/Down and Enter selection;
- restore focus to the trigger when closed;
- show a compact no-results message.

Load this script only on the Admin shift form, Admin roster planner, Admin recurring shift form, and worker service log form.

- [ ] **Step 5: Add scoped responsive styling**

Append component-scoped rules to \`static/css/app.css\` for:

- a compact trigger matching current form controls;
- a bounded dropdown with internal scrolling;
- restrained uppercase category headings;
- regular \`400\` weight option text;
- subtle separators, hover, selected, and keyboard focus states;
- wrapped long labels with no horizontal page overflow;
- mobile-safe positioning and minimum tap targets.

- [ ] **Step 6: Run focused tests and verify they pass**

Run the Task 1 test command.

Expected: PASS for all form contract and template activation assertions.

- [ ] **Step 7: Commit the UI component**

\`\`\`powershell
git add templates/scheduling/partials/support_item_picker_field.html static/js/support_item_picker.js static/css/app.css templates/scheduling/partials/shift_form_fields.html templates/scheduling/recurring_shift_form.html templates/service_logs/worker_service_log_form.html templates/scheduling/shift_form.html templates/scheduling/roster_planner.html scheduling/tests_support_item_picker.py service_logs/tests_support_item_picker.py
git commit -m "feat: add searchable support item picker"
\`\`\`

### Task 3: Verify Behaviour And Responsive Presentation

**Files:**
- Modify only if verification exposes a defect in files from Tasks 1-2.

- [ ] **Step 1: Run scheduling, service-log, and invoice regression tests**

\`\`\`powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py test scheduling.tests_shifts scheduling.tests_recurring_shifts scheduling.tests_support_item_picker service_logs.tests_service_logs service_logs.tests_support_item_picker invoices.tests_invoices
\`\`\`

Expected: PASS with zero failures.

- [ ] **Step 2: Run Django and diff checks**

\`\`\`powershell
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' manage.py check
git diff --check origin/main...HEAD
\`\`\`

Expected: no Django issues and no whitespace errors.

- [ ] **Step 3: Perform browser verification**

Start the local server, then verify Admin shift create/edit, planner modal, recurring shift, and SW Unscheduled Service at desktop and mobile widths. Confirm exact label text, category grouping, search, keyboard selection, selected-value persistence, validation errors, scrolling, and no horizontal overflow. Confirm Support Coordination invoice remains native and unchanged.

- [ ] **Step 4: Commit any verification fixes**

If Task 3 finds a defect, write a failing regression test first, make the smallest fix, rerun the relevant suite, and commit only those files.

- [ ] **Step 5: Create and attach the pull request**

Push \`codex/support-item-picker-style\`, create a PR against \`main\`, and attach the PR to the task for the user to merge.
