# Manual Test Report #010

| Field | Value |
|-------|-------|
| **Report ID** | MT-010 |
| **Date** | 2026-04-26 |
| **Tester** | Noddie Mgbodille + external student testers |
| **Test Case ID** | MT-10 |
| **Requirement ID** | FR-Privacy-Consent, FR-4.1 (Consent toggles and recognition/privacy behavior) |

---

## Test Steps

1. Share the deployed application URL with external student testers and have them create accounts.
2. Create or join an event where consent controls are available.
3. Open the event consent sheet and inspect the profile visibility and recognition toggles.
4. Toggle profile visibility off and verify the app communicates the visibility impact clearly.
5. Toggle recognition on and off and verify the app enforces any prerequisites and updates the UI state correctly.
6. Re-open the consent sheet and event views to confirm the saved state persists.
7. Repeat the flow with multiple users to validate that privacy-related behavior is consistent.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Consent toggles should save reliably and reflect the current state when reopened | Initial manual testing exposed consent-related bugs that were later fixed; after fixes, toggle state persisted correctly | Yes, after fix |
| Recognition-related consent should enforce the intended privacy rules | Testers confirmed the privacy behavior aligned with the intended consent rules after fixes | Yes |
| UI should make the effect of the toggles understandable to users | Testers were able to understand what each toggle did and what impact it had on profile visibility and recognition | Yes |
| Multi-user behavior should stay consistent when privacy preferences differ between users | Testers reported the behavior was consistent after the consent fixes were applied | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- Live feedback from student testers exercising consent controls in the deployed app.
- Follow-up verification after consent-related bugs were fixed.
- Supporting automated regression coverage: [`backend/tests/test_consents_update.py`](../../../backend/tests/test_consents_update.py)

---

## Next Steps

1. Keep consent toggle behavior under regression tests whenever event privacy rules change.
2. Add more automated checks around multi-user privacy visibility scenarios where feasible.
