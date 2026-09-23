# Support Item Picker Presentation Design

## Goal

Make long NDIS support item lists easier to scan and select without changing which support items are available, what value is submitted, or how shifts, service logs, and invoices use that value.

The approved presentation is a compact searchable dropdown with visual category headings, regular-weight item rows, restrained separators, and a bounded scroll area.

## Scope

Apply the presentation enhancement to:

- Admin single shift create and edit forms.
- Admin recurring shift form.
- Support Worker Unscheduled Service form.

Do not apply it to:

- Support Coordination invoice forms.
- Invoice creation, preview, export, or calculation screens.
- Support item management pages.
- Any other select field.

## Non-Negotiable Data Contract

The existing Django support item field remains the source of truth.

- Keep the same field name, HTML value, selected primary key, required state, queryset, ordering, server-side validation, and POST behaviour.
- Keep `SupportItem.active_items()` as the available choice set in every in-scope form.
- Keep the existing model and `SupportItem.__str__()` output unchanged.
- Preserve every option label verbatim and in its existing sequence. The visible format remains:

  `item code - description - Standard - rate period`

  For example:

  `01_011_0107_1_1 - Assistance With Self-Care Activities - Standard - Weekday Daytime`

- Do not abbreviate, reorder, split, rewrite, or reconstruct the option text.
- The submitted value remains the existing `SupportItem` primary key, so invoice linkage and downstream invoice line generation remain unchanged.
- No model, migration, pricing, GST, invoice, service-log calculation, or scheduling rule changes are permitted.

## Presentation Behaviour

Use progressive enhancement around the existing Django `<select>`.

- JavaScript reads the options already rendered by Django; it does not fetch, add, remove, or replace support items.
- The existing select remains in the document and remains the submitted form control.
- The enhanced control mirrors the select value in both directions and dispatches the normal `change` event after a user selection.
- If JavaScript is unavailable or fails, the original select remains usable.
- Existing bound values and validation errors remain visible after an unsuccessful form submission.

The enhanced dropdown contains:

- A compact trigger displaying the exact selected option text.
- A search input that filters the currently rendered options by their full existing label, including item code, description, and rate period.
- Non-selectable category headings based only on the existing `SupportItem.category` value.
- An `Other support items` heading for items whose existing category is blank.
- Regular-weight item rows. Category headings may use a stronger label treatment, but item descriptions must not be bold.
- Subtle row separators and hover/focus highlighting.
- A constrained-height results panel with internal scrolling so the page layout does not expand with the list.
- A clear empty-search message without modifying the underlying option set.

The grouping is visual only. It must not change database ordering or the order of options within each category.

## Responsive And Accessible Behaviour

- Keep the dropdown within the form viewport on desktop and mobile.
- Long labels may wrap naturally; they must not cause horizontal page scrolling.
- Preserve a comfortable minimum tap target on the Support Worker mobile form.
- Support pointer and keyboard use: open, move through options, select, close with Escape, and return focus to the trigger.
- Expose the trigger/search/results relationship with appropriate combobox and listbox semantics and announce the selected item.
- Use visible focus styling consistent with the existing teal interface.

## Implementation Boundary

Prefer one reusable presentation component shared by the in-scope templates. Activation should be explicit through a widget class or data attribute on the existing support item field, so unrelated selects and invoice forms cannot be enhanced accidentally.

The implementation may add scoped CSS and JavaScript plus minimal template/widget attributes. It must not alter business-domain Python code beyond presentation metadata needed to activate the component or expose existing category text for visual grouping.

## Verification

Automated coverage should prove:

- Admin single and recurring shift forms still expose the same active support item IDs and labels.
- The Support Worker Unscheduled Service form still exposes and submits the same active support item IDs.
- Bound forms retain the selected support item and show existing validation errors.
- The enhancement is activated only on the three in-scope form surfaces.
- Invoice and Support Coordination forms remain unchanged.
- The option label is rendered verbatim, including code, description, `Standard`, and rate period.
- The page remains functional with the enhancement script absent.

Manual responsive verification should cover desktop Admin and mobile Support Worker layouts, including long option labels, search with no results, keyboard selection, and reopening an already selected value.

## Out Of Scope

- Changing support item records or categories.
- Automatically choosing an item from date, time, service type, participant, or worker.
- Filtering choices by weekday, public holiday, service type, participant, or rate.
- Changing invoice mapping or calculation behaviour.
- Adding the picker to the Support Coordinator invoice flow.
- Replacing server-side validation with client-side validation.
