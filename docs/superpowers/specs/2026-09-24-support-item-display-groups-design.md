# Support Item Display Groups Design

## Goal

Replace the overly broad `Core Supports` heading in the searchable support item picker with service-family headings that help users scan the list quickly.

## Display structure

The picker groups matching support items under these presentation-only headings:

- Self-care
- Community access
- Provider travel
- Support coordination

Each selectable option keeps its exact existing `item number - name - rate period` label. The selected option value remains the existing `SupportItem` primary key.

## Data safety

The existing `SupportItem.category`, item number, name, price, invoice relationships, and form querysets remain unchanged. A small helper derives the picker heading from the item's existing name. Unknown Core items use `Other core supports`; other unknown items retain their stored category, or use `Other support items` when the category is blank.

## Visual treatment

Group headings remain compact, sticky dividers. Option text is reduced slightly while desktop and mobile touch-target heights remain unchanged.

## Verification

Tests cover all four display groups, fallback behavior, unchanged option labels and values, and the Admin and Support Worker forms that use the picker.
