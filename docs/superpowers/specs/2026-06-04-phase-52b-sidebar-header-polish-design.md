# Phase 52B Sidebar and Header Polish Design

## Goal
Make the admin shell visibly more polished while keeping functionality untouched.

## Scope
This phase focuses on the global shell:

- Sidebar brand treatment
- Sidebar navigation spacing and active state
- Topbar separation
- Page header spacing and action alignment

## Safety Rules
This phase must not copy Tabler source code or import Tabler assets. It must not change models, views, URLs, permissions, form field names, or workflow logic.

## Implementation
CSS changes live in `static/css/app.css`. `templates/admin_base.html` gets only minor presentational markup for the brand subtitle.

## Testing
Existing dashboard tests continue to verify the shell renders and active navigation works.
