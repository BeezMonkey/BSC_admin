# Phase 5 Support Item Management Design

## Scope

Phase 5 adds admin-managed NDIS support items as operational configuration for later scheduling, service logs, and invoices.

Included:
- `SupportItem` model.
- Admin-only support item list with search and active/category filters.
- Support item create, edit, and detail pages.
- Django Admin registration.
- Tests for permissions, creation, validation, editing, filtering, and active item helper.

Excluded for this phase:
- Automatic NDIS price guide import.
- Price guide version history.
- Shift, service log, or invoice linkage.
- Invoice line generation.

## Data Model

`SupportItem` stores:
- item number
- name
- category
- unit
- price limit
- GST code
- active flag
- notes
- timestamps

The system does not invent real NDIS support item numbers. Admin users enter and verify item numbers manually.

`unit` values:
- `hour`
- `each`
- `km`

`gst_code` values:
- `gst_free`
- `taxable`

`item_number` must be unique.

## Pages

`/settings/support-items/`
Admin-only list. Supports search by item number/name/category, active filter, and category filter.

`/settings/support-items/new/`
Admin-only create form.

`/settings/support-items/<id>/`
Admin-only detail page.

`/settings/support-items/<id>/edit/`
Admin-only edit form.

## Permission Rules

Only Super Admin and Admin can access support item management in this phase. Support Worker and Accountant receive HTTP 403.

## Testing

Tests cover:
- Admin can create support item.
- Item number is required and unique.
- Price limit must not be negative.
- Admin can filter/search support items.
- Admin can edit support item.
- Detail page displays item configuration.
- Active queryset/helper returns active items only.
- Worker and Accountant cannot access support item pages.
