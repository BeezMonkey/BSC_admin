# BSC Admin Phase Index

Last updated: 2026-08-28

This file is the working index for BSC Admin phase branches, PRs, and recovery points. Use it to understand what each phase changed, where to find it on GitHub, and which stable version can be used as a restore point.

## Current Stable Restore Point

| Type | Name | Notes |
| --- | --- | --- |
| Stable tag | `stable-2026-08-28-phase-129` | Stable checkpoint after Phase 129A was merged. |
| Backup branch | `codex/backup-2026-08-28-stable-phase-129` | GitHub branch pointing at the same stable code as `main` after Phase 129A. |
| Local bundle | `C:/Users/sinop/Documents/bsc-admin-backups/bsc-admin-stable-2026-08-28-phase-129.bundle` | Offline Git recovery package. Use only if GitHub restore points are unavailable. |

Current stable commit:

```text
0c63de5 Merge pull request #173 from BeezMonkey/codex/phase-129a-worker-menu-icon-polish
```

## How To Use This Index

- Search by `phase-129a`, `#173`, or a feature keyword such as `invoice`, `worker`, `roster`, or `mobile`.
- Use the `Branch` column to find the exact GitHub branch.
- Use the `PR` column to find the merged pull request.
- Use the `Purpose` column to understand the business or UI reason for that phase.
- For rollback, prefer the stable tag or backup branch above.

## Phase Groups

| Range | Area | Summary |
| --- | --- | --- |
| Phase 0-12C | Product foundation | Django setup, permissions, participants, workers, assignments, support items, scheduling, service logs, invoices, documents, audit, production readiness. |
| Phase 13-29B | V1 readiness and invoice basics | QA polish, demo data, workflow review, invoice filters, service-log invoice shortcut, bulk invoice creation, PDF amount formatting. |
| Phase 30-51 | Workflow and list usability | Worker shift UX, dashboard summaries, roster filters, pagination, sorting, return-state preservation, checkbox/status polish. |
| Phase 52A-67 | Admin UI foundation and QA | Sidebar/header/table/form polish, system messages, upload forms, roster/service log readability, Australian date/time, Brisbane timezone, staging docs. |
| Phase 68-79 | Beta readiness | Dashboard onboarding, light theme, Render beta handoff, public health check, beta seed data, trial pack. |
| Phase 80-92 | Roster planner | Roster operations, recurring shifts, quick planner, weekly grid, shift modal, copy/paste/delete/edit. Phase 92 was later reverted. |
| Phase 93-109 | Invoice and billing | Invoice settings, logo, PDF layout, global numbering, demo invoice seed, travel claims. |
| Phase 110-118 | Demo reset and worker archive | Noon display fix, safe demo reset, support item protection, worker list simplification, login wording, archived workers and scheduling safety. |
| Phase 120-124 | Invoice PDF hardening | Description wrapping, line-item polish, service-date column, footer, multi-page pagination. |
| Phase 125A-129A | Worker mobile experience | Responsive drawer navigation, mobile content, service-log form containment, iOS Safari time input fixes, shift card action hierarchy, menu icon polish. |
| Phase 130-131 | Product documentation | Phase progress index and BSC UI Design System v1. |
| Phase 132 | Worker mobile QA polish | Worker mobile shift flow accessibility and narrow-screen layout refinements. |
| Phase 133 | Admin table polish | Create Invoice table empty state, filter placeholder, alignment, and table density polish. |
| Phase 134 | Admin table system polish | Shared Admin filter, button, table density, and numeric alignment polish. |

## Recent Detailed Index

| PR | Date | Branch | Purpose |
| --- | --- | --- | --- |
| Current | 2026-08-28 | `codex/phase-134-admin-table-filter-system-polish` | Unifies Admin list filter rows, buttons, table density, action alignment, and numeric cells. |
| #177 | 2026-08-28 | `codex/phase-133-admin-table-filter-polish` | Polished the Create Invoice filter row, empty state, and preview table density. |
| #176 | 2026-08-28 | `codex/phase-132-worker-mobile-flow-qa-polish` | Refined worker mobile shift flow accessibility and narrow-screen layout resilience. |
| #175 | 2026-08-28 | `codex/phase-131-ui-design-system-v1` | Added the BSC UI Design System v1 documentation for future UI work. |
| #174 | 2026-08-28 | `codex/phase-130-phase-index-doc` | Added the phase progress index. |
| #173 | 2026-08-27 | `codex/phase-129a-worker-menu-icon-polish` | Polished the worker mobile menu icon. |
| #172 | 2026-08-27 | `codex/phase-128a-worker-shift-action-first` | Refined worker shift cards so primary actions are clearer and faster to use. |
| #171 | 2026-08-27 | `codex/phase-127a-worker-shifts-mobile-actions` | Improved mobile shift-card action placement. |
| #170 | 2026-08-27 | `codex/phase-126b-worker-detail-mobile-polish` | Polished worker shift/detail mobile flow. |
| #169 | 2026-08-27 | `codex/phase-126a-worker-shifts-mobile-polish` | Polished worker My Shifts mobile layout. |
| #168 | 2026-08-27 | `codex/phase-125f-worker-ios-time-input-safari` | Added iOS Safari-specific time input containment. |
| #167 | 2026-08-27 | `codex/phase-125e-worker-ios-time-input-fix` | Tightened worker iOS time input layout. |
| #166 | 2026-08-27 | `codex/phase-125d-worker-mobile-input-containment` | Fixed mobile service-log input overflow. |
| #165 | 2026-08-27 | `codex/phase-125c-worker-service-log-mobile-polish` | Polished worker service-log mobile form. |
| #164 | 2026-08-26 | `codex/phase-125b-worker-mobile-content-polish` | Polished worker mobile content density and hierarchy. |
| #163 | 2026-08-26 | `codex/phase-125a-worker-responsive-navigation` | Added worker responsive drawer navigation. |
| #162 | 2026-08-26 | `codex/phase-124-invoice-pdf-pagination` | Fixed multi-line invoice PDF pagination. |
| #161 | 2026-08-21 | `codex/phase-123-invoice-pdf-footer-polish` | Polished invoice PDF footer. |
| #160 | 2026-08-21 | `codex/phase-122-invoice-pdf-service-date-column` | Replaced the generic item column with the service date column in invoice PDFs. |
| #159 | 2026-08-21 | `codex/phase-121-invoice-line-table-polish` | Polished invoice PDF line items. |
| #158 | 2026-08-21 | `codex/phase-120-invoice-description-wrap` | Wrapped long invoice PDF descriptions safely. |
| #157 | 2026-08-19 | `codex/phase-118-worker-access-archive-copy` | Clarified worker access and archive wording. |
| #156 | 2026-08-19 | `codex/phase-117-archived-worker-scheduling-safety` | Prevented archived workers from being scheduled into new shifts. |
| #155 | 2026-08-19 | `codex/phase-116-worker-archive-view` | Added archived worker list view. |
| #154 | 2026-08-19 | `codex/phase-115-worker-account-access-section` | Moved worker account access controls to the form footer area. |
| #153 | 2026-08-19 | `codex/phase-114-worker-login-status-wording` | Clarified worker login status copy. |
| #152 | 2026-08-19 | `codex/phase-113-worker-list-simplification` | Simplified support worker list information. |
| #151 | 2026-08-18 | `codex/phase-112-reset-demo-protected-items` | Protected/reset legacy demo support item references. |
| #150 | 2026-08-18 | `codex/phase-111-reset-beta-demo-data` | Added safe beta demo data reset. |
| #149 | 2026-08-01 | `codex/phase-110-time-display-format` | Fixed noon display so times show numerically instead of `noon`. |
| #148 | 2026-07-31 | `codex/phase-109-support-items-travel-claim` | Added support items and travel claim handling for invoices. |
| #147 | 2026-07-22 | `codex/phase-108-invoice-demo-seed` | Added invoice demo seed command. |
| #146 | 2026-07-22 | `codex/phase-107-global-invoice-numbering` | Added global invoice numbering sequence. |

## Full Phase Branch Index

| Phase | Branch | Branch title / main content |
| --- | --- | --- |
| 0 | `codex/phase-0-django-foundation` | Django project foundation. |
| 1 | `codex/phase-1-permissions` | Role access controls. |
| 2 | `codex/phase-2-participants` | Participant management. |
| 3 | `codex/phase-3-workers` | Support worker management. |
| 4 | `codex/phase-4-assignments` | Participant-worker assignments. |
| 5 | `codex/phase-5-support-items` | Support item management. |
| 6 | `codex/phase-6-scheduling` | Basic scheduling. |
| 7 | `codex/phase-7-service-logs` | Service logs. |
| 8 | `codex/phase-8-service-log-review` | Service log review. |
| 9 | `codex/phase-9-invoices` | Invoice generation. |
| 10 | `codex/phase-10-invoice-exports` | Invoice exports. |
| 11 | `codex/phase-11-recurring-shifts` | Recurring shifts. |
| 12 | `codex/phase-12-documents` | Document management. |
| 12B | `codex/phase-12b-audit-hardening` | Audit hardening. |
| 12C | `codex/phase-12c-production-readiness` | Production readiness. |
| 13 | `codex/phase-13-v1-qa-polish` | V1 QA polish. |
| 14 | `codex/phase-14-ui-layout-polish` | Table action alignment. |
| 15 | `codex/phase-15-demo-readiness` | Local demo data seed command. |
| 16 | `codex/phase-16-worker-shell-polish` | Worker shell aligned with admin layout. |
| 17A | `codex/phase-17a-second-demo-case` | Second demo data case. |
| 17B | `codex/phase-17b-list-actions` | View actions for logs and invoices. |
| 18A | `codex/phase-18a-list-display-polish` | Invoice list display polish. |
| 18B | `codex/phase-18b-detail-navigation` | Back links on detail pages. |
| 18C | `codex/phase-18c-empty-states` | Empty state guidance. |
| 19 | `codex/phase-19-v1-trial-docs` | V1 trial release notes. |
| 20 | `codex/phase-20-pre-deployment-review` | Pre-deployment readiness review. |
| 21 | `codex/phase-21-staging-deployment-plan` | Staging deployment plan. |
| 22 | `codex/phase-22-ui-consistency-polish` | Button sizing normalization. |
| 23 | `codex/phase-23-ui-qa-pass` | UI QA polish pass. |
| 24 | `codex/phase-24-template-theme-evaluation` | Template/theme evaluation. |
| 25 | `codex/phase-25-business-workflow-review` | Business workflow review. |
| 26 | `codex/phase-26-workflow-readiness-panels` | Workflow readiness panels. |
| 27 | `codex/phase-27-invoice-management-filters` | Invoice management filters. |
| 28 | `codex/phase-28-service-log-invoice-shortcut` | Service log to invoice shortcut. |
| 28B | `codex/phase-28b-invoice-form-alignment` | Invoice preview filter form alignment. |
| 29 | `codex/phase-29-bulk-service-log-invoice` | Bulk service log invoicing. |
| 29B | `codex/phase-29b-pdf-amount-formatting` | Invoice PDF amount formatting. |
| 30 | `codex/phase-30-worker-shift-status-ux` | Worker shift status visibility. |
| 31 | `codex/phase-31-worker-shift-quick-actions` | Worker shift quick actions. |
| 32 | `codex/phase-32-worker-shift-filters` | Worker shift list filters. |
| 33 | `codex/phase-33-worker-dashboard-summary` | Worker dashboard action summary. |
| 34 | `codex/phase-34-admin-dashboard-summary` | Admin dashboard operations summary. |
| 35 | `codex/phase-35-dashboard-plural-labels` | Dashboard summary label polish. |
| 36 | `codex/phase-36-dashboard-zero-states` | Dashboard zero states. |
| 37 | `codex/phase-37-dashboard-filter-context` | Dashboard filter context on lists. |
| 38 | `codex/phase-38-multi-filter-summary` | Multi-filter list summaries. |
| 39 | `codex/phase-39-roster-worker-filter-select` | Worker select in roster filter. |
| 40 | `codex/phase-40-roster-name-filters` | Roster name search filters. |
| 41 | `codex/phase-41-roster-filter-usability` | Roster filter wording. |
| 42 | `codex/phase-42-roster-expanded-keyword-filters` | Expanded roster keyword filters. |
| 43 | `codex/phase-43-list-pagination-usability` | Pagination for core admin lists. |
| 44 | `codex/phase-44-log-invoice-pagination` | Pagination for service logs and invoices. |
| 45 | `codex/phase-45-list-sorting-basics` | Sortable admin lists. |
| 46 | `codex/phase-46-empty-state-filter-feedback` | Filtered empty states. |
| 47 | `codex/phase-47-preserve-list-return-state` | Preserve list return state. |
| 48 | `codex/phase-48-edit-return-state` | Preserve edit return state. |
| 49 | `codex/phase-49-create-return-state` | Preserve create return state. |
| 50 | `codex/phase-50-checkbox-polish` | Checkbox padding reset. |
| 51 | `codex/phase-51-status-pill-colors` | Semantic status pill colors. |
| 52A | `codex/phase-52a-tabler-inspired-ui-foundation` | Tabler-inspired UI foundation. |
| 52B | `codex/phase-52b-sidebar-header-polish` | Sidebar and page header polish. |
| 52C | `codex/phase-52c-table-list-polish` | Table and list view polish. |
| 52D | `codex/phase-52d-form-detail-polish` | Form and detail page polish. |
| 52E | `codex/phase-52e-empty-pagination-polish` | Empty states and pagination polish. |
| 52F | `codex/phase-52f-system-messages-polish` | System messages and form field alignment. |
| 53 | `codex/phase-53-ui-qa-review-checklist` | UI QA checklist. |
| 54A | `codex/phase-54a-table-action-button-consistency` | Table action button consistency. |
| 54B | `codex/phase-54b-ui-qa-findings-log` | UI QA findings log. |
| 55A | `codex/phase-55a-worker-responsive-polish` | Worker responsive layout polish. |
| 55B | `codex/phase-55b-service-logs-table-density` | Service logs table density. |
| 56A | `codex/phase-56a-worker-mobile-qa-polish` | Active worker sidebar link highlight. |
| 56B | `codex/phase-56b-admin-sidebar-active-polish` | Admin sidebar active states. |
| 57A | `codex/phase-57a-admin-form-table-polish-qa` | Small-screen invoice preview wrapping. |
| 57B | `codex/phase-57b-document-upload-form-polish` | Document upload form layout. |
| 58A | `codex/phase-58a-recurring-shift-form-polish` | Recurring shift form layout. |
| 58B | `codex/phase-58b-recurring-shift-helper-text` | Recurring shift helper text. |
| 59A | `codex/phase-59a-roster-workflow-polish-qa` | Shift detail spacing. |
| 59B | `codex/phase-59b-roster-cancel-section-polish` | Roster cancel section polish. |
| 60A | `codex/phase-60a-shift-detail-info-polish` | Shift detail information polish. |
| 60B | `codex/phase-60b-roster-list-readability-polish` | Roster list readability. |
| 61A | `codex/phase-61a-service-logs-list-readability-polish` | Service logs list readability. |
| 61B | `codex/phase-61b-service-log-au-date-format` | Australian service log dates. |
| 61C | `codex/phase-61c-au-date-format-audit` | Australian dates on main lists. |
| 61D | `codex/phase-61d-detail-worker-au-dates` | Australian dates on detail surfaces. |
| 62 | `codex/phase-62-date-time-export-format` | Australian datetime formats in audits and exports. |
| 63 | `codex/phase-63-brisbane-timezone` | Brisbane business timezone. |
| 64 | `codex/phase-64-environment-config-guardrails` | Environment config guardrails. |
| 65 | `codex/phase-65-staging-runbook` | Staging deployment runbook. |
| 66 | `codex/phase-66-smoke-test-matrix` | Staging smoke test matrix. |
| 67 | `codex/phase-67-trial-feedback-template` | Trial feedback template. |
| 68 | `codex/phase-68-dashboard-onboarding` | Dashboard workflow checklist. |
| 69 | `codex/phase-69-dashboard-visual-refinement` | Admin dashboard overview refinement. |
| 70 | `codex/phase-70-light-visual-foundation` | Light visual foundation. |
| 71 | `codex/phase-71-light-theme-visual-qa` | Light theme visual QA. |
| 72 | `codex/phase-72-dashboard-checklist-alignment` | Dashboard workflow checklist alignment. |
| 73 | `codex/phase-73-admin-light-theme-qa` | Admin light theme QA pass. |
| 74A | `codex/phase-74a-theme-color-trial` | Softer healthcare theme color trial. |
| 74B | `codex/phase-74b-typography-spacing-refinement` | Theme typography and spacing. |
| 74C | `codex/phase-74c-theme-refresh-qa` | Theme refresh QA pass. |
| 75 | `codex/phase-75-deployment-readiness` | Render beta deployment readiness. |
| 76 | `codex/phase-76-render-beta-handoff` | Render beta handoff checklist. |
| 77 | `codex/phase-77-public-health-check` | Public deployment health routes. |
| 78 | `codex/phase-78-beta-test-data-seed` | Safe beta test data seed. |
| 79 | `codex/phase-79-beta-trial-pack` | Beta trial pack. |
| 80 | `codex/phase-80-roster-operational-polish` | Roster operations polish. |
| 81 | `codex/phase-81-recurring-shift-management` | Recurring shift draft/publish management. |
| 82 | `codex/phase-82-roster-publish-safety` | Roster draft publish action clarity. |
| 83A | `codex/phase-83a-quick-roster-planner` | Quick roster planner view. |
| 83B | `codex/phase-83b-planner-date-grid` | Planner date grid. |
| 83C | `codex/phase-83c-planner-add-shift-links` | Planner day shift links. |
| 83D | `codex/phase-83d-planner-shift-defaults` | Planner shift defaults. |
| 83E | `codex/phase-83e-planner-weekly-grid` | Weekly planner grid. |
| 83F | `codex/phase-83f-planner-scroll-density` | Planner shift tile density. |
| 84A | `codex/phase-84a-planner-view-mode` | Planner view mode and light admin UI foundation. |
| 85 | `codex/phase-85-roster-planner-compact-ui` | Compact roster planner week view. |
| 86 | `codex/phase-86-shift-modal` | Roster planner shift modal. |
| 87 | `codex/phase-87-shift-modal-field-polish` | Shift modal placeholder polish. |
| 88A | `codex/phase-88a-shift-copy-as-new` | Planner shift action icons and copy-as-new flow. |
| 88B | `codex/phase-88b-shift-copy-paste` | Planner copy/paste accent polish. |
| 89 | `codex/phase-89-planner-delete-shift` | Planner shift delete action. |
| 90 | `codex/phase-90-delete-confirm-modal` | Planner delete confirmation polish. |
| 91 | `codex/phase-91-planner-edit-modal` | Planner edit shift modal. |
| 92 | `codex/phase-92-planner-action-layout-polish` | Planner action layout polish. Later reverted by PR #128 and #129. |
| 93 | `codex/phase-93-invoice-settings` | Invoice settings billing profile. |
| 94 | `codex/phase-94-invoice-logo-field-polish` | Invoice logo preview safety. |
| 95 | `codex/phase-95-invoice-pdf-layout` | Invoice settings details in PDF. |
| 96 | `codex/phase-96-invoice-pdf-polish` | Invoice PDF layout polish. |
| 97 | `codex/phase-97-invoice-pdf-header-reference` | Invoice PDF typography/header reference. |
| 98 | `codex/phase-98-invoice-pdf-header-spacing` | Invoice PDF header alignment. |
| 99 | `codex/phase-99-invoice-pdf-header-tightening` | Invoice PDF header spacing tightened. |
| 100 | `codex/phase-100-invoice-pdf-header-cleanup` | Invoice PDF header block cleanup. |
| 101 | `codex/phase-101-invoice-pdf-flow-spacing` | Line items flow after billing details. |
| 102 | `codex/phase-102-invoice-pdf-text-weight-spacing` | PDF detail text weight/spacing. |
| 103 | `codex/phase-103-invoice-pdf-line-items-table` | PDF line items table polish. |
| 104 | `codex/phase-104-invoice-pdf-payment-details` | PDF payment details polish. |
| 105 | `codex/phase-105-invoice-pdf-static-logo` | Static invoice PDF logo asset. |
| 106 | `codex/phase-106-invoice-pdf-header-polish` | Invoice PDF header spacing polish. |
| 107 | `codex/phase-107-global-invoice-numbering` | Global invoice numbering sequence. |
| 108 | `codex/phase-108-invoice-demo-seed` | Invoice demo seed command. |
| 109 | `codex/phase-109-support-items-travel-claim` | Support items and travel claims in invoices. |
| 110 | `codex/phase-110-time-display-format` | Numeric display for noon times. |
| 111 | `codex/phase-111-reset-beta-demo-data` | Safe beta demo data reset. |
| 112 | `codex/phase-112-reset-demo-protected-items` | Protected demo support item references. |
| 113 | `codex/phase-113-worker-list-simplification` | Simplified support worker list. |
| 114 | `codex/phase-114-worker-login-status-wording` | Worker login status wording. |
| 115 | `codex/phase-115-worker-account-access-section` | Worker account access controls moved to form footer. |
| 116 | `codex/phase-116-worker-archive-view` | Archived worker list view. |
| 117 | `codex/phase-117-archived-worker-scheduling-safety` | Archived worker scheduling restriction. |
| 118 | `codex/phase-118-worker-access-archive-copy` | Worker access/archive wording. |
| 120 | `codex/phase-120-invoice-description-wrap` | Invoice PDF description wrapping. |
| 121 | `codex/phase-121-invoice-line-table-polish` | Invoice PDF line item polish. |
| 122 | `codex/phase-122-invoice-pdf-service-date-column` | Service date column in invoice PDF table. |
| 123 | `codex/phase-123-invoice-pdf-footer-polish` | Invoice PDF footer polish. |
| 124 | `codex/phase-124-invoice-pdf-pagination` | Multi-page invoice PDF pagination. |
| 125A | `codex/phase-125a-worker-responsive-navigation` | Worker responsive drawer navigation. |
| 125B | `codex/phase-125b-worker-mobile-content-polish` | Worker mobile content polish. |
| 125C | `codex/phase-125c-worker-service-log-mobile-polish` | Worker service log mobile form polish. |
| 125D | `codex/phase-125d-worker-mobile-input-containment` | Worker mobile input containment. |
| 125E | `codex/phase-125e-worker-ios-time-input-fix` | iOS time input layout fix. |
| 125F | `codex/phase-125f-worker-ios-time-input-safari` | iOS Safari time input containment. |
| 126A | `codex/phase-126a-worker-shifts-mobile-polish` | Worker shifts mobile layout polish. |
| 126B | `codex/phase-126b-worker-detail-mobile-polish` | Worker detail mobile flow polish. |
| 127A | `codex/phase-127a-worker-shifts-mobile-actions` | Worker mobile shift card actions. |
| 128A | `codex/phase-128a-worker-shift-action-first` | Worker shift action hierarchy. |
| 129A | `codex/phase-129a-worker-menu-icon-polish` | Worker mobile menu icon polish. |
| 130 | `codex/phase-130-phase-index-doc` | Phase progress index documentation. |
| 131 | `codex/phase-131-ui-design-system-v1` | BSC UI Design System v1 documentation. |
| 132 | `codex/phase-132-worker-mobile-flow-qa-polish` | Worker mobile shift flow accessibility and narrow-screen layout polish. |
| 133 | `codex/phase-133-admin-table-filter-polish` | Create Invoice filter, empty state, and preview table polish. |
| 134 | `codex/phase-134-admin-table-filter-system-polish` | Shared Admin table, filter, button, and numeric alignment polish. |

## Notes

- There is no merged `phase-119` branch in the current remote phase list.
- Some branches were merged more than once during iterative QA, for example `phase-83f`, `phase-84a`, `phase-88a`, `phase-88b`, `phase-94`, and `phase-97`.
- `phase-92-planner-action-layout-polish` was merged and then reverted through PR #128 and #129.
- This file is a navigation aid. Git remains the source of truth for exact code changes.
