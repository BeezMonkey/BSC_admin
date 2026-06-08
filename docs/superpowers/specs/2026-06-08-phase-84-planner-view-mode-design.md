# Phase 84 Planner View Mode Design

## Goal

Improve Quick Roster Planner so admins can plan from two practical perspectives:

- Participant view: review each participant's scheduled service dates and assigned workers.
- Worker view: review each support worker's working days and assigned participants.

Phase 84C fortnight horizontal timeline is intentionally out of scope for now.

## Scope

### Phase 84A: Planner View Mode

Add a view mode control to the Quick Roster Planner:

- `Participant view`
- `Worker view`

The existing planner page remains the entry point. The page should continue using the current 7-day grid layout and existing date filters.

In Participant view:

- The primary selector is Participant.
- The optional secondary selector is Worker.
- Each shift card should make the participant context clear and show the assigned worker.

In Worker view:

- The primary selector is Worker.
- The optional secondary selector is Participant.
- Each shift card should make the worker context clear and show the participant receiving support.

The underlying query can continue using the existing participant and worker filters. The main change is to make the intent explicit and adjust the labels/context shown on the planner.

### Phase 84B: Shift Card Actions

Add safe actions to each shift card:

- `View`: opens shift detail.
- `Edit`: opens the existing shift edit form.
- `Copy`: opens the shift create form prefilled from the selected shift.
- `Delete`: available only for Draft shifts.

Non-draft shifts must not be hard deleted from the planner. Published, confirmed, completed, cancelled, and no-show shifts should keep the existing record trail. A future cancel workflow can handle operational cancellation.

## UX Notes

- Keep the planner familiar and lightweight.
- Do not introduce the Vertex360-style fortnight horizontal timeline in this phase.
- Keep the `+` day action for adding a new shift on that date.
- Put per-shift actions inside the shift card, not beside the day-level `+`, so the user can clearly tell whether an action affects the whole day or one shift.
- Prefer short labels over icons for now because this system is still being tested by real staff.

## Data And Safety

- No database schema change is required for Phase 84A.
- Copy should reuse the existing shift form and pass prefill parameters in the URL or through a small server-side helper.
- Delete should require POST and CSRF protection.
- Draft delete should write an audit log.
- Copy should not create anything until the user saves the new shift form.

## Testing

Add tests for:

- Participant view renders and preserves the selected view mode.
- Worker view renders and preserves the selected view mode.
- Worker view can filter by worker and show matching shifts.
- Shift cards expose View/Edit/Copy links.
- Draft shifts expose Delete.
- Non-draft shifts do not expose Delete.
- Copy opens the create form with original shift fields prefilled.

## Rollout

Implement Phase 84A first and merge it before Phase 84B. This keeps the core planner view change separate from record-changing operations like copy/delete.
