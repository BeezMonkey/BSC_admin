# Phase 52A Tabler-Inspired UI Foundation Design

## Goal
Improve the admin interface polish using Tabler as a visual reference while preserving the existing Django structure and business behavior.

## Scope
This phase is intentionally limited to low-risk foundation styling:

- System font stack
- Slightly cleaner color tokens
- Card, table, button, form, and page spacing polish
- Sidebar navigation active state
- No copied Tabler HTML, CSS, or JavaScript

## Safety Rules
The Tabler template in `reference_templates/` is reference-only and must not be committed. This phase must not introduce Bootstrap, Tabler assets, Tabler scripts, new form field names, URL changes, permission changes, model changes, or view workflow changes.

## Implementation
Most changes live in `static/css/app.css`. `templates/admin_base.html` only receives minimal class additions and route checks for active navigation highlighting.

## Testing
Tests verify that the active sidebar class appears on the current admin page. Existing app tests verify that business behavior remains unchanged.
