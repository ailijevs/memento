# Manual Test Report #011

| Field | Value |
|-------|-------|
| **Report ID** | MT-011 |
| **Date** | 2026-04-26 |
| **Tester** | Noddie Mgbodille + external student testers |
| **Test Case ID** | MT-11 |
| **Requirement ID** | FR-Privacy-Consent, UX-Privacy-Clarity |

---

## Test Steps

1. Share the application URL with external student testers who were not involved in implementation.
2. Ask the testers to create accounts and navigate through event-related flows without prior explanation.
3. Have them review the consent controls and event UI copy that explains privacy and recognition behavior.
4. Ask them to describe, in their own words, what happens when profile visibility or recognition is enabled or disabled.
5. Verify whether their understanding matches the intended privacy model of the app.
6. Collect confusion points, unclear wording, or places where the UI could better explain privacy effects.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Users should understand the basic privacy implications of the consent toggles from the UI alone | Testers were generally able to explain the privacy behavior correctly using only the UI text and flow context | Yes |
| The app should communicate that consent choices affect profile visibility and recognition behavior | Testers understood that the toggles controlled whether their profile could be shown and whether recognition features could use their data | Yes |
| The privacy model should feel understandable enough for normal users, not just developers | Testers reported the privacy behavior was understandable after interacting with the consent UI | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- Qualitative tester feedback gathered during live usage of the deployed application.
- Observations from user explanations of toggle behavior and privacy consequences.

---

## Next Steps

1. Refine UI copy further if future testers show confusion around consent language.
2. Re-run this kind of manual privacy-comprehension check after major consent or recognition UX changes.
