# Manual Test Report #001

| Field | Value |
|-------|-------|
| **Report ID** | MT-001 |
| **Date** | 2026-02-01 |
| **Tester** | Marty Ilijevski |
| **Test Case ID** | MT-01 |
| **Requirement ID** | FR-2.1 (Resume upload populates profile fields) |

---

## Test Steps

1. Start the backend locally: `cd backend && uvicorn app.main:app --reload`
2. Obtain a valid JWT by signing up via Supabase Auth
3. Upload a PDF resume to `POST /api/v1/profiles/me/resume` with `Authorization: Bearer <token>`
4. Check the API response `extracted_data` for all expected fields
5. Query the `profiles` table on Supabase to verify the fields were persisted

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Response contains `full_name`, `headline`, `bio`, `company`, `major`, `graduation_year` | All six fields present in `extracted_data` | Yes |
| Response contains `location`, `profile_one_liner`, `profile_summary` | **Before fix:** missing from response. **After fix (Issue #195):** present | Yes (after fix) |
| Response contains `experiences` and `education` arrays | **Before fix:** missing. **After fix:** present with correct entries | Yes (after fix) |
| `profile_updated` is `true` | `true` | Yes |
| Supabase `profiles` row has `location`, `profile_one_liner`, `profile_summary`, `experiences`, `education` | **Before fix:** these columns were NULL despite being parsed. **After fix:** all populated | Yes (after fix) |

---

## Outcome

- [x] **Pass** (after Issue #195 fix applied)
- [ ] **Fail**

---

## Defect Found

Before the fix on branch `fix/resume-parser-fields-195`, this test **failed**. The resume parser correctly extracted all fields via OpenAI GPT-4o-mini, but the `upload_resume` endpoint in `backend/app/api/profiles.py` only saved `full_name`, `headline`, `bio`, `company`, `major`, and `graduation_year` to the database. Five fields were silently dropped:

- `location`
- `profile_one_liner`
- `profile_summary`
- `experiences`
- `education`

This was logged as **Issue #195** and fixed by adding the missing fields to both the update and create code paths in `upload_resume`.

---

## Logs / Screenshots / Evidence

```bash
# Before fix — response missing fields
$ curl -s -X POST http://localhost:8000/api/v1/profiles/me/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@resume.pdf" | python -m json.tool

{
  "message": "Resume parsed successfully",
  "extracted_data": {
    "full_name": "Marty Ilijevski",
    "headline": "Software Engineer",
    "bio": "Experienced full-stack developer...",
    "company": "Memento",
    "major": "Computer Science",
    "graduation_year": 2026,
    "email": "marty@example.com",
    "skills": ["Python", "React", "AWS"]
  },
  "profile_updated": true
}
# NOTE: location, profile_one_liner, profile_summary, experiences,
# education are ALL missing from extracted_data

# After fix — all fields present
$ curl -s -X POST http://localhost:8000/api/v1/profiles/me/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@resume.pdf" | python -m json.tool

{
  "message": "Resume parsed successfully",
  "extracted_data": {
    "full_name": "Marty Ilijevski",
    "headline": "Software Engineer",
    "bio": "Experienced full-stack developer...",
    "company": "Memento",
    "major": "Computer Science",
    "graduation_year": 2026,
    "location": "West Lafayette, IN",
    "email": "marty@example.com",
    "skills": ["Python", "React", "AWS"],
    "profile_one_liner": "Building the future of networking.",
    "profile_summary": "Full-stack engineer specializing in AI-driven...",
    "experiences": [{"company": "Memento", "title": "Lead Engineer", ...}],
    "education": [{"school": "Purdue University", "degree": "BS", ...}]
  },
  "profile_updated": true
}
```

---

## Next Steps

- Issue #195 fix merged; re-test passes.
- Add automated regression test: `TestResumeUploadFieldPersistence` in `backend/tests/test_resume_parser.py` now covers this permanently.
