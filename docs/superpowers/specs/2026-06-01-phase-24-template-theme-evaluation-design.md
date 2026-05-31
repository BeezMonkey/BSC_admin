# Phase 24 Template Theme Evaluation Design

## Purpose

Phase 24 evaluates whether and how the project should adopt a fuller admin template or theme in the future. It does not change the current UI implementation.

## Scope

- Record UI/template requirements for this NDIS admin system.
- Compare the current custom CSS approach with open-source admin template options.
- Identify template integration risks.
- Define a safe future migration path.
- Keep the current application behavior and styling unchanged.

## Out Of Scope

- Downloading or installing a template.
- Purchasing a paid template.
- Replacing Django templates.
- Changing navigation, permissions, models, forms, or business workflows.
- Adding JavaScript frameworks.

## Approach

The system should remain operationally focused rather than marketing-like. Any future template must support dense forms, tables, filters, status badges, detail pages, and worker-facing pages. The safest path is to choose a design system first, then migrate shell, tables, forms, and dashboard cards in separate phases.

## Recommendation

Do not integrate a full third-party theme immediately. Continue using the current custom CSS while preparing a future theme integration plan. If a third-party template is selected later, prefer a Bootstrap 5 style system with permissive licensing, minimal JavaScript requirements, and clean HTML examples that can be adapted to Django templates.

## Verification

This is documentation-only. Verify that the documentation links are present and Django system checks still pass.
