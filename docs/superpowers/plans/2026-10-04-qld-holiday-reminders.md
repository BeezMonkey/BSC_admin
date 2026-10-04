# Queensland Holiday Reminders Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. The visual design and scope were approved in the conversation on 4 October 2026.

**Goal:** Add advisory Queensland, Brisbane, Logan and Gold Coast holiday labels to the admin planner and scheduling calendars, retaining all existing scheduling and billing decisions.

**Architecture:** One source-verified, versioned JSON calendar feeds Python template tags and opt-in JavaScript calendar decoration. No model, migration, form validation, permission, invoice or rate-selection changes. Planner styles remain scoped to existing planner classes. Worker and SC calendars do not opt in.

**Tech Stack:** Django templates, Python standard library, existing plain JavaScript date picker, CSS, Django and Node tests.

## Approved Design

- All three planner views share the same card styling: time, primary name, secondary detail, separator, status and existing actions. Keep lowercase am/pm and bind each suffix to its time.
- Existing status colors, conflict warnings, multi-worker labels, copy/edit/view/delete permissions and multi-week layout remain.
- Holiday names and explicit region labels appear in date headings, including dates with no shifts. Statewide and regional labels use distinct subdued colors.
- Admin create/edit/copy date pickers show holiday marks, accessible names and selected-date reminders. Recurring previews show holiday information on each matching date.
- Christmas Eve states 6 pm to midnight, never all day. Additional/substitute holidays retain their official dates.
- Unknown coverage displays a warning, not a claim that no holiday exists. Data is bundled, with official sources and verification date, not fetched during page loads.
- Reminder text leaves support-item and rate selection manual. Demo database records and standalone HTML prototypes must not enter the implementation commit.

## Tasks

- [x] **1. Data and Python presentation helpers.** Added the versioned calendar, read-only Python helpers, template tags and 28 data tests. Verified 2026 coverage for all four regions and 2027 statewide/Brisbane coverage; unverified regions produce a warning.
- [x] **2. Template and style integration.** Added shared badges/assets, all three planner headings, scheduling form reminders and recurring preview labels. Existing actions, permissions and manual support-item selection remain. Added six integration tests.
- [x] **3. Opt-in calendar decoration.** Added presentation-only helpers and scoped CSS. Calendar-grid coverage includes adjacent-year dates. Eight Node tests verify labels, part-day detail, unknown coverage and no form-value mutation or change events.
- [x] **4. Verify and preview.** Completed automated suites and local browser checks using an isolated demo database. Main and staging remain unchanged.

## Verification Results

- Django: 574 tests, 573 passed and one PostgreSQL row-lock concurrency test skipped on SQLite. Test-only overrides use MD5 password hashing and plain static-file storage for speed; application settings are unchanged.
- Node: all 18 tests passed, including the existing SC calendar-positioning suite.
- Django system checks, migration dry run and static collection passed. No migration is needed.
- Browser: checked daily, participant and worker views, multi-week alignment, 320/390/768/1440 px layouts, modal create/copy dates, selection/clear, unchanged support item, recurring date selection, Christmas Eve hours and cross-year warnings. Recurring preview labels and unchanged holiday shift pricing are covered by Django tests.
- Read-only specification and quality reviews completed. The cross-year coverage finding was fixed and regression-tested; final review reported no actionable findings.
- Real iPhone Safari and screen-reader behavior were not directly tested. Holiday data must be maintained as later regional dates are published.

## Sources and Maintenance

- https://www.qld.gov.au/recreation/travel/holidays/public
- https://www.qld.gov.au/recreation/travel/holidays/show

Review the JSON against those official pages when adding a year. Do not extrapolate local show dates. Include a test for each regional entry and a coverage-warning test for unknown years.
