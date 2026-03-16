# Manual Test Report #003 — User Acceptance Test

| Field | Value |
|-------|-------|
| **Report ID** | MT-003 (UAT) |
| **Date** | 2026-02-01 |
| **Tester** | Marty Ilijevski |
| **Test Case ID** | UAT-01 |
| **Requirement ID** | FR-2.1, FR-2.3 (User can upload resume during onboarding and profile is populated) |

---

## User Story

> As a new user, I want to upload my resume during onboarding so that my profile is automatically populated with my name, headline, location, experiences, and education without manual data entry.

---

## Preconditions

- Backend running locally (`uvicorn app.main:app --reload`)
- Frontend running locally (`npm run dev`)
- User has a valid Google or email account for sign-up
- User has a PDF or DOCX resume file ready

---

## Test Steps

| Step | Action | Expected Result | Actual Result | Pass? |
|------|--------|-----------------|---------------|-------|
| 1 | Navigate to the app and click "Sign Up" | Sign-up page loads | Sign-up page loads with email and Google options | Yes |
| 2 | Sign up with Google OAuth | Redirect to Google, then back to onboarding page | Google OAuth completes, redirected to `/onboarding` | Yes |
| 3 | On the onboarding page, select "Upload Resume" option | File upload dialog appears | Upload interface shown with "PDF or DOCX" instructions | Yes |
| 4 | Upload a PDF resume (standard text-based) | Resume is parsed, profile preview shows extracted data | Preview shows full_name, headline, bio, location, experiences, education | Yes |
| 5 | Review the profile preview — verify all fields are filled | name, headline, bio, location, one-liner, summary, experiences, education should all be populated | All fields populated correctly from resume (after Issue #195 fix) | Yes |
| 6 | Edit the full_name field on the preview to correct a typo | Field becomes editable, user can type correction | Inline editing works, field updates in real-time (Issue #212 feature) | Yes |
| 7 | Click "Continue" to save the profile | Profile is saved to Supabase, user is redirected to dashboard | Profile saved successfully, dashboard loads | Yes |
| 8 | Navigate to Supabase dashboard and check the `profiles` table | All fields including `location`, `profile_one_liner`, `profile_summary`, `experiences`, `education` are populated | All columns contain the extracted data | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Acceptance Criteria Verification

| Criterion | Met? |
|-----------|------|
| Resume upload accepts PDF and DOCX formats | Yes |
| Extracted data populates all profile fields (including location, one-liner, summary, experiences, education) | Yes (after #195 fix) |
| User can review and edit extracted data before saving | Yes (#212 feature) |
| Profile is persisted to Supabase `profiles` table | Yes |
| Invalid file types (e.g., .txt, .jpg) are rejected with clear error message | Yes |

---

## Evidence

- **Code**: [`backend/app/api/profiles.py` — `upload_resume` endpoint](https://github.com/ailijevs/memento/blob/main/backend/app/api/profiles.py)
- **Resume Parser**: [`backend/app/services/resume_parser.py`](https://github.com/ailijevs/memento/blob/main/backend/app/services/resume_parser.py)
- **Bug found during UAT**: Issue [#195](https://github.com/ailijevs/memento/issues/195) — five fields were extracted but not saved. Fixed on branch `fix/resume-parser-fields-195`.
- **Automated regression tests**: [`backend/tests/test_resume_parser.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py)

---

## Notes

This UAT was conducted end-to-end after the resume parsing feature and profile card builder were integrated. During the initial UAT run, the tester discovered Issue #195 (missing profile fields) which was subsequently fixed and regression-tested. The UAT was re-run after the fix and all acceptance criteria now pass.
