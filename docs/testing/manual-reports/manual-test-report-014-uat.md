# Manual Test Report #014 — User Acceptance Test

| Field | Value |
|-------|-------|
| **Report ID** | MT-014 (UAT) |
| **Date** | 2026-04-20 |
| **Tester** | Marty |
| **Test Case ID** | UAT-02 |
| **Requirement ID** | FR-1.1 (User sign-up and email verification flow) |

---

## User Story

> As a new user signing up with email/password, I want to receive a verification email with a valid confirmation link so I can activate my account and access the app.

---

## Preconditions

- Frontend is running locally (`npm run dev`) or deployed environment is reachable.
- Backend and Supabase Auth are configured for email sign-up.
- At least one temporary inbox provider is accessible (used only for delivery/verification validation).
- Browser has no active authenticated session for the app.

---

## Test Steps

| Step | Action | Expected Result | Actual Result | Pass? |
|------|--------|-----------------|---------------|-------|
| 1 | Open app and navigate to Sign Up | Sign-up screen loads with email/password option | Sign-up page loaded correctly | Yes |
| 2 | Enter a valid temporary email + password, submit sign-up | Account creation request accepted and app prompts for email confirmation | Sign-up accepted and verification prompt shown | Yes |
| 3 | Open the temporary inbox and wait for verification email | Verification email arrives within normal delivery window | Verification email received | Yes |
| 4 | Open email and inspect verification link target | Link points to expected Supabase/app auth confirmation flow | Link target was correct and valid | Yes |
| 5 | Click verification link from email | Browser redirects to app/auth callback and marks account as verified | Redirect completed and account verified | Yes |
| 6 | Return to app and attempt login with verified credentials | Login succeeds and user reaches authenticated app area | Login succeeded and user entered app | Yes |
| 7 | Repeat with a second temporary email to confirm consistency | Same behavior: email delivered, link works, login succeeds | Second run passed with identical behavior | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Acceptance Criteria Verification

| Criterion | Met? |
|-----------|------|
| Email/password sign-up creates a pending account | Yes |
| Verification email is delivered to inbox | Yes |
| Verification email contains a valid confirmation link | Yes |
| Clicking the link completes account verification | Yes |
| Verified account can log in successfully | Yes |

---

## Evidence

- **Frontend sign-up flow**: [`frontend/src/components/signup-content.tsx`](https://github.com/ailijevs/memento/blob/main/frontend/src/components/signup-content.tsx)
- **Frontend integration coverage**: [`frontend/src/components/__tests__/signup-content.test.tsx`](https://github.com/ailijevs/memento/blob/main/frontend/src/components/__tests__/signup-content.test.tsx)
- **Auth dependency**: Supabase Auth email confirmation flow validated manually end-to-end.

---

## Notes

This UAT specifically validates real-world delivery and click-through behavior of verification emails. Temporary inbox accounts were used to independently confirm that verification messages are actually sent and that confirmation links are functional across multiple runs.
