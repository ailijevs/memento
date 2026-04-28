# Manual Test Report #012

| Field | Value |
|-------|-------|
| **Report ID** | MT-012 |
| **Date** | 2026-04-26 |
| **Tester** | Noddie Mgbodille |
| **Test Case ID** | MT-12 |
| **Requirement ID** | FR-Recognition-Storage (Profile photo upload and retrieval flow) |

---

## Test Steps

1. Sign in to the application with a valid user account.
2. Navigate to the profile or onboarding flow where a profile photo can be uploaded.
3. Select a valid image file and trigger the profile photo upload flow.
4. Verify that the upload completes successfully and the UI reflects the new profile photo.
5. Refresh or revisit the profile view to confirm the photo persists after reload.
6. Confirm that the backend can still resolve the uploaded photo into a usable signed URL for display.
7. Repeat the flow with a replacement photo to verify the existing stored photo is replaced cleanly.
8. Attempt an invalid or incomplete upload case and verify the app responds with a clear error instead of silently failing.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| User can upload a valid profile image successfully | Valid profile image upload completed successfully and the new photo appeared in the app | Yes |
| Uploaded photo should persist and remain visible after refresh/revisit | Uploaded profile photo remained associated with the user and displayed correctly after revisiting the page | Yes |
| Re-uploading a new photo should replace the previous one cleanly | Replacement upload updated the visible profile photo as expected | Yes |
| Retrieval/display path should resolve the stored photo for the frontend correctly | The app was able to display the uploaded photo after the backend resolved the stored object path | Yes |
| Invalid or failed upload path should produce a visible error state | Error behavior was understandable and did not leave the UI in a misleading state | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- Manual verification through the deployed app UI during profile photo upload and replacement flow.
- Supporting automated regression coverage:
  - [`backend/tests/test_profile_photo_upload_url.py`](../../../backend/tests/test_profile_photo_upload_url.py)
  - [`backend/tests/test_live_s3_integrations.py`](../../../backend/tests/test_live_s3_integrations.py)

---

## Next Steps

1. Keep both API-layer and live S3 integration coverage in place as the upload flow evolves.
2. Add additional negative-path automation for malformed files or interrupted uploads if those regressions start appearing.
