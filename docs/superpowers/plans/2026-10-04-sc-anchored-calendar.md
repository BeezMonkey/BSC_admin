# SC Anchored Calendar and Compact Controls

> **For agentic workers:** Use test-driven development with independent implementation review. Reuse the current SC revisions worktree; preserve its other pending changes.

**Goal:** Keep the SC calendar next to its date field at every width, unify SC selection control states, and make duration inputs compact and aligned.

**Architecture:** Add a `sc-log-form` class only to the SC create/edit form. A separate `sc_date_picker.js` positions its existing calendar using viewport coordinates, leaving the shared calendar's date parsing, selection and dismissal intact. Keep all overrides in SC-only CSS/assets. Do not edit shared picker JS, shared CSS, SW/Roster templates or backend behavior.

**Tech Stack:** Django templates/tests, scoped CSS, browser DOM events, Node built-in tests, browser responsive checks.

## Approved Behavior

- Default calendar placement is immediately below its trigger with a small gap; use the space above if below is insufficient.
- Clamp horizontally to the visible viewport. Reserve space for the visible fixed mobile header/navigation. If neither side can fit the full calendar, constrain its height and allow internal scrolling.
- Reposition on page/container scrolling, window/visual viewport changes, and calendar month size changes. Close through the existing trigger when it leaves the usable viewport.
- Preserve click-outside, Escape, month navigation, Today/Clear and date serialization. No new date parser or duplicate calendar.
- Only SC create/edit load the enhancement. Normal selects retain native selection. Match selection borders, hover/focus ring and pointer cursor, with visible validation/disabled states.
- Limit the duration pair to a compact width, align its legend/inputs with the other fields, and retain mobile 44px touch height and zero-clearing behavior.
- Local preview only: no commits, push, deployment, database reset or saved demo submissions.

## Tasks

- [x] Add Django assertions that SC create/edit opt in and SW/Roster templates do not load SC assets. Add Node tests for below/above placement, viewport edges, insufficient space, scrolling, month resize, dismissal and unrelated-picker exclusion. RED confirmed: 9 new Node behaviors failed; SC markup assertions failed for both create/edit.
- [x] Add the SC form class and deferred script after the shared picker. Implement SC-only placement using `getBoundingClientRect`, fixed viewport coordinates, throttled animation frames, viewport/header/nav bounds, and existing-trigger dismissal. Node tests: 10 passed. Duration/form tests: 14 passed.
- [x] Update only `static/css/sc_log_form.css`: consistent select/date states, 44px mobile targets, compact duration pair and aligned label rhythm; override the shared mobile bottom-fixed layout only within `.sc-log-form`. CSS implemented independently and ready for browser verification.
- [x] Run Node tests and full Django regression suite: 10 Node tests passed; 768 Django tests passed and 1 PostgreSQL-only test skipped. Independent specification and code-quality reviews found no actionable issues. `git diff --check` passed; shared picker, SW and Roster source files remain unchanged.
- [x] Collect static assets and restart only the isolated local8004 server. Existing demo DB and user input tabs preserved; no records submitted during QA.
- [x] Browser verified 390px, 660px and 1280px: 6px below/above gap, scroll tracking and offscreen dismissal, longer November calendar, constrained internal scrolling, date selection, Today/Clear, Escape and click-outside. New/edit forms verified; disabled participant remains locked and selected text uses normal ink. Temporary viewport override reset. Real iOS Safari hardware remains untested.

## Verification Commands

From the existing SC worktree:

```powershell
node --test tests/js/sc_date_picker.test.cjs
& 'C:\Users\sinop\Documents\bsc admin\.venv\Scripts\python.exe' 'C:\Users\sinop\AppData\Local\Temp\bsc-follow-up-tests.py' coordinators service_logs scheduling
git diff --check
```

Browser checks use temporary tabs with existing local sessions, without saving any records. Source changes to common picker files must remain absent from the final delta.
