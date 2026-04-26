# Manual Test Report #009

| Field | Value |
|-------|-------|
| **Report ID** | MT-009 |
| **Date** | 2026-04-26 |
| **Tester** | Sasha |
| **Test Case ID** | MT-09 |
| **Requirement ID** | FR-4.3 (Compatibility scoring), FR-4.1 (Profile card display) |

---

## Test Steps

1. Start the backend locally: `cd backend && uvicorn app.main:app --reload`
2. Start the frontend locally: `cd frontend && npm run dev`
3. Log in as a test attendee who has joined an active event
4. Navigate to the event dashboard and open the profile directory
5. Verify that profile cards are sorted by descending compatibility score (highest match shown first)
6. Check that a card for a user sharing the same company shows a higher score than a card for a user with no overlap
7. Enter a name in the search field and confirm that only matching profiles are shown
8. Toggle the sort to "Recent" and confirm the order changes to show most-recently-enrolled profiles first
9. Confirm that users with `allow_profile_display = false` do not appear in any sort order
10. Clear the search field and confirm all visible profiles return

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Profiles are sorted by compatibility score descending by default | Cards appear in descending score order; shared-company card ranked first | Yes |
| Shared-company card shows score badge ≥ 30 | Score badge shows "30% match" for a user sharing only company | Yes |
| Search filters cards by name substring | Entering partial name reduces the displayed cards to matching entries only | Yes |
| Toggling to "Recent" reorders cards by join date | Cards reordered with most recent enrollees first; scores still visible but not used for sort | Yes |
| Consent-gated profiles (`allow_profile_display = false`) are excluded | No cards appeared for the test user with display consent disabled | Yes |
| Clearing search restores full list | All consented profiles reappear after clearing the search input | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

Manual test executed locally with the backend at `http://localhost:8000` and frontend at `http://localhost:3000`. The profile directory endpoint used is `GET /api/v1/profiles/directory/{event_id}`, which is covered by automated integration tests in `backend/tests/test_profiles_event_directory.py` and `backend/tests/test_consents_update.py`.

Compatibility scoring for each directory entry is driven by `GET /api/v1/profiles/{user_id}/compatibility`, tested in `backend/tests/test_compatibility_endpoint.py`.

---

## Next Steps

- Automated regression tests for the directory endpoint and compatibility scoring are in place in CI.
- Edge case to add: test sort stability when two profiles have identical compatibility scores.
