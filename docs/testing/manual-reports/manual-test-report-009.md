# Manual Test Report #009

| Field | Value |
|-------|-------|
| **Report ID** | MT-009 |
| **Date** | 2026-04-26 |
| **Tester** | Noddie Mgbodille + external student testers |
| **Test Case ID** | MT-09 |
| **Requirement ID** | FR-3.1, FR-3.2 (Event creation, update, deletion, and membership flow) |

---

## Test Steps

1. Share the deployed application URL with two external student testers.
2. Have each tester create an account and sign in normally.
3. Ask one tester to create an event with standard required fields and verify it appears in their dashboard.
4. Ask the event creator to edit the event details and verify the updated values persist in the UI.
5. Ask a second tester to join the event and confirm the event appears in their event list.
6. Ask the second tester to leave the event and verify the membership state updates correctly.
7. Ask the event creator to delete the event and verify it is removed from active views.
8. Repeat the flow with small variations in event data to surface validation or state bugs.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| New users can create accounts and reach the event dashboard | Testers were able to sign up and access the event dashboard successfully | Yes |
| Event creation should succeed and persist correctly | Initial manual run exposed event creation issues in some cases; these were fixed and the flow was re-tested successfully | Yes, after fix |
| Event edits should persist and show updated details in the UI | Updated event details appeared correctly after save | Yes |
| Joining and leaving an event should update membership state correctly | Testers were able to join and leave the event, and state changes were reflected in the UI | Yes |
| Event deletion should remove the event from active views | Creator was able to delete the event and it no longer appeared in active event lists | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- Live tester feedback from external student users during account creation and event workflow execution.
- Local bug-fix verification after issues were found in event creation behavior.
- Supporting automated regression coverage: [`backend/tests/test_event_time_guards.py`](../../../backend/tests/test_event_time_guards.py)

---

## Next Steps

1. Keep event creation and membership flows in regression coverage whenever event validation or lifecycle logic changes.
2. Add more automated route-level coverage for event CRUD edge cases found during manual testing.
