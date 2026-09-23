# Portal Date and Time Style Design

## Goal

Use the approved Admin date calendar and five-minute time wheel styling in the Support Worker and Support Coordinator work-entry forms without changing their business logic, validation, field names, or submitted values.

## Scope

The change applies only to these portal forms:

- Support Worker `Complete Service Log`: actual start and end time.
- Support Worker `Submit Unscheduled Service`: service date plus actual start and end time.
- Support Coordinator `Submit Coordination Log`: service date plus start and end time.

Admin profile, assignment, roster filter, invoice, participant, and document date fields are outside this change.

## Design

The existing shared `templates/scheduling/partials/date_time_picker_field.html` markup and `static/js/date_time_picker.js` behaviour will be reused. Each portal template will render its existing Django fields through that partial and load the shared script once.

The controls retain the approved presentation:

- compact calendar with Saturday and Sunday emphasis;
- hour, five-minute, and AM/PM time wheels;
- responsive placement on desktop and mobile;
- existing labels, errors, and helper copy appropriate to each portal.

Portal-specific CSS may adjust only layout integration, such as grid width, stacking, and popup layering. The picker dimensions and interaction styling remain shared with Admin.

## Data And Behaviour Preservation

The original Django form classes remain authoritative. The rendered controls continue to submit through hidden inputs using the existing field names:

- `service_date` as `YYYY-MM-DD`;
- `actual_start_time`, `actual_end_time`, `start_time`, and `end_time` as 24-hour values accepted by the current forms.

No model, view, URL, status transition, duration calculation, break handling, participant assignment, or form validation code will change. Existing initial values and validation errors remain visible through the shared component.

## Accessibility And Responsive Behaviour

Triggers retain programmatic labels and expanded state. The calendar and time controls preserve keyboard focus indicators, Escape and outside-click dismissal, and readable selected states. At mobile widths, popovers remain contained within the viewport and do not obscure the form action area.

## Verification

Template tests will first assert that the SW and SC forms render the shared picker contract while preserving their existing field names. Existing form and workflow tests will verify that submissions, calculations, validation, and redirects remain unchanged. Browser checks will cover SW scheduled and unscheduled forms plus the SC coordination form at desktop and mobile widths.
