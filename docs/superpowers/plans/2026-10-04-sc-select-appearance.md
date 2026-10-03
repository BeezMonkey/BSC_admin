# SC Select Appearance Implementation Plan

**Goal:** Give SC Participant and Coordination type the same muted dropdown arrow without changing form behavior.

**Architecture:** Keep native select elements, choices and defaults. Add a CSS-only arrow to the two named selects inside `.sc-log-form`; retain the existing shared selection-control dimensions, borders, focus and placeholder rules. Do not change shared CSS, JavaScript, backend or Support Worker templates.

**Tech Stack:** Django, scoped CSS, browser computed-style checks.

- [x] Inspect rendered styles before editing. Both selects currently have native `appearance: auto`, no independent arrow image, and different text colors. The portal already resolves all three selection controls to 5px radius, so leave radius unchanged.
- [x] Add regression coverage for the existing Coordination type default, available choices and edit preselection. All 15 duration/form tests passed.
- [x] In `static/css/sc_log_form.css`, replace background shorthand with background-color in shared states to retain arrow images. Add `appearance: none`, right padding and two small gray CSS triangles forming a downward chevron only on the two native selects. In forced-colors mode restore the native arrow. Browser checks confirmed independent identical arrow images and unchanged selected/placeholder text colors.
- [x] Bump only the SC form stylesheet cache version to 4. Static assets collected; only the verified isolated preview resume process was restarted. No demo records submitted.
- [x] Ran 59 coordinator duration/revision/form tests and 10 Node calendar tests; all passed. `git diff --check` passed. Browser verified identical arrow images before/after keyboard selection and focus; desktop, 660px and 390px widths; 44px mobile controls; no horizontal overflow; anchored calendar still 6px from date field; disabled participant preserved on edit. No browser errors, saved preview records, commits or pushes. Real-device Safari and forced-colors rendering were not tested.
