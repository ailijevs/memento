# Manual Test Report #002

| Field | Value |
|-------|-------|
| **Report ID** | MT-002 |
| **Date** | 2026-01-28 |
| **Tester** | Marty Ilijevski |
| **Test Case ID** | MT-02 |
| **Requirement ID** | FR-4.1 (Recognition returns profile card data) |

---

## Test Steps

1. Start the backend locally: `cd backend && uvicorn app.main:app --reload`
2. Ensure at least one user is enrolled in the Rekognition collection (via seed data or manual enrollment)
3. Capture a base64-encoded JPEG frame of a known enrolled user
4. POST to `/api/v1/recognition/detect` with `{"image_base64": "<base64>", "event_id": null}`
5. Verify the response contains `ProfileCard` objects (not raw `FaceMatch` data)
6. Verify each `ProfileCard` includes condensed fields (`full_name`, `headline`, `company`, `photo_path`, `face_similarity`) and detail fields (`bio`, `experiences`, `education`, `linkedin_url`)

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Response `matches` array contains `ProfileCard` objects | `matches` contains objects with `full_name`, `headline`, `face_similarity`, etc. | Yes |
| Each card has `face_similarity` (renamed from `similarity`) | `face_similarity` field present with correct percentage | Yes |
| Each card has `experience_similarity` (nullable) | Field present, value `null` (not yet implemented) | Yes |
| Detail fields (`bio`, `location`, `experiences`, `education`) are populated from the profiles table | All fields populated for enrolled users | Yes |
| Cards for users without `allow_profile_display` consent are excluded when `event_id` is provided | Tested with consent disabled; card correctly omitted | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

```bash
$ curl -s -X POST http://localhost:8000/api/v1/recognition/detect \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "'$(cat frame.b64)'", "event_id": null}' | python -m json.tool

{
  "matches": [
    {
      "user_id": "a1b2c3d4-...",
      "full_name": "Akash Kumar",
      "headline": "Computer Engineering Student at Purdue",
      "company": null,
      "photo_path": "profiles/a1b2c3d4-onboarding.jpg",
      "profile_one_liner": "Aspiring embedded systems engineer.",
      "face_similarity": 95.32,
      "experience_similarity": null,
      "bio": "Junior studying computer engineering...",
      "location": "West Lafayette, IN",
      "major": "Computer Engineering",
      "graduation_year": 2027,
      "linkedin_url": "https://linkedin.com/in/akashkumar",
      "profile_summary": "Computer engineering student...",
      "experiences": [{"company": "Purdue ECE", "title": "TA"}],
      "education": [{"school": "Purdue University", "degree": "BS"}]
    }
  ],
  "processing_time_ms": 487.2,
  "event_id": null
}
```

---

## Next Steps

- No failures; profile card builder working as designed.
- Automated regression tests exist in `backend/tests/test_recognition.py` (`TestDetectEndpoint`) and `backend/tests/test_resume_parser.py` (`TestProfileCardBuilder`).
