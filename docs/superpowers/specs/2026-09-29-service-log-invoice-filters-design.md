# Service Log Invoice Filters Design

## Goal

Make the admin Service Logs page faster to use when preparing invoices by allowing an administrator to show one participant's service records within a service-date period.

The change must preserve the existing service-log review, approval, rejection, selection, and invoice-creation rules.

## Approved Interface

The existing status overview cards remain the only status selector. The duplicate `Status` dropdown is removed.

A single compact filter row sits between the status overview cards and the Billing action panel. It contains, in order:

1. `Participant`: a single-select list. The blank option is `All participants`.
2. `Date range`: a preset selector.
3. `Service date from`: a date field.
4. `Service date to`: a date field.
5. `Filter` and `Clear` actions.

The row uses the existing admin form-control styling and remains compact on desktop. It wraps cleanly on narrow screens without changing the service-log table or mobile portal layouts.

Below the controls, a small result summary shows the number of matching records and the sum of their actual hours, for example `Showing 6 approved logs · 22.5 hours`.

## Filter Behaviour

### Participant

- Only one participant can be selected at a time.
- Selecting a participant shows only service logs belonging to that participant.
- The participant list includes all participants, ordered by display name, so historical records remain findable even if a participant is no longer active.
- With no participant selected, records for all participants remain visible.

### Service Date

All date filtering applies to `ServiceLog.service_date`. Submitted timestamps do not affect the results.

The `Date range` selector contains:

- `All dates`: no date restriction and the default for the existing unfiltered page.
- `This week`: Monday through Sunday of the current Brisbane week.
- `Last week`: Monday through Sunday immediately before the current week.
- `This fortnight`: Monday of the current week through Sunday of the following week.
- `Last fortnight`: the fourteen days ending on the Sunday immediately before the current week.
- `This month`: first through last calendar day of the current Brisbane month.
- `Last month`: first through last calendar day of the previous month.
- `Custom`: uses the entered From and To dates inclusively.

For a preset, the server calculates and displays the effective From and To values. For `Custom`, either boundary may be omitted; an omitted boundary leaves that side open.

Invalid dates do not produce a server error. They are ignored as filter bounds and the page continues to render with the entered value available for correction.

## Status Cards

- The existing `All logs`, `Submitted`, `Approved`, `Invoiced`, and `Rejected` cards continue to control status.
- Card counts remain the existing global status totals.
- Clicking a status card preserves the selected participant and date filters.
- The active card remains visually marked.

## Clear, Sorting, and Pagination

- `Clear` removes the participant and date filters while retaining the currently selected status card.
- Column sorting preserves status, participant, date range, and effective date values.
- Pagination preserves the same filters and sort order.
- The current record-selection and `Create Invoice from Selected` behaviour is unchanged.
- Only approved rows remain selectable for invoice creation.
- Existing invoice validation continues to require selected service logs to belong to one participant and the invoice period.

## Result Summary

The summary is calculated from the complete filtered queryset before pagination. It includes:

- matching record count;
- active status wording when a status card is selected; and
- total `actual_hours` across matching records.

The summary is informational only and does not change which rows are eligible for invoicing.

## Data Flow

1. The browser sends filter values as GET query parameters.
2. `service_log_list` validates and normalises the participant and date parameters.
3. The view applies status, participant, and inclusive service-date filters to the existing queryset.
4. The filtered queryset supplies the summary, sorting, pagination, and rendered table.
5. Template links retain the active query parameters where required.

No database migration or model change is required.

## Error and Empty States

- An unknown participant ID behaves as no participant match and renders an empty filtered result rather than exposing another record or raising an error.
- An invalid preset value falls back to `All dates`.
- A custom From date later than the To date returns an empty result with the normal filtered-empty message.
- The existing distinction between an empty database and no matches for active filters remains intact.

## Testing

Automated tests will cover:

- filtering by one participant;
- filtering inclusively by service date;
- every date-range preset using a fixed current date;
- custom open-ended and reversed date ranges;
- invalid participant and date input;
- status-card links preserving participant and date filters;
- Clear retaining status while removing participant and dates;
- sorting and pagination preserving all filters;
- summary count and actual-hours total using the full filtered queryset;
- removal of the duplicate status dropdown; and
- unchanged invoice selection eligibility.

The focused Service Logs test suite and relevant theme/template tests must pass before creating the pull request.

## Out of Scope

- Changes to approval, rejection, or worker submission workflows.
- Changes to invoice generation, invoice line calculation, or invoice PDF output.
- Multi-participant selection.
- Filtering by submitted date.
- New database fields or migrations.
