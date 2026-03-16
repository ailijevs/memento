# Verification Test Inventory

> This table lists every test from the Requirements Verification Traceability Matrix (RVTM). Automated tests run in CI on every push and PR. Manual tests are documented in `docs/testing/manual-reports/`.

## Test Documentation Location

- **`docs/testing/`** – Verification Test Inventory, manual test template, manual test reports
- **`backend/tests/`** – Automated unit/integration tests (pytest)
- **`docs/testing/manual-reports/`** – Manual test reports with evidence

---

## Table 1 – Verification Test Inventory

| Test Case ID | Requirement ID | Description | Tool | Owner | Automated? | CI Integrated? | Evidence Link |
|--------------|----------------|-------------|------|-------|------------|----------------|---------------|
| UT-01 | FR-3.1 | Root and health endpoints return correct status | pytest | Team | Yes | Yes | [`backend/tests/test_main.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_main.py) |
| UT-02 | FR-1.1 | Auth endpoints require valid JWT | pytest | Team | Yes | Yes | [`backend/tests/test_auth.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_auth.py) |
| UT-03 | FR-2.1 | Resume parser regex fallback extracts name, email, phone | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestResumeParserRegexFallback](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| UT-04 | FR-2.1 | Resume parser sanitizes strings correctly | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestResumeParserSanitize](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| UT-05 | FR-2.1 | Resume upload saves ALL extracted fields to DB (Issue #195 fix) | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestResumeUploadFieldPersistence](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| UT-06 | FR-4.1 | ProfileCardBuilder constructs cards from recognition matches | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestProfileCardBuilder](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| UT-07 | FR-4.1 | Recognition schemas validate FaceMatch and ProfileCard | pytest | Marty | Yes | Yes | [`backend/tests/test_recognition.py` — TestFaceMatchSchema, TestFrameDetectionResponseSchema](https://github.com/ailijevs/memento/blob/main/backend/tests/test_recognition.py) |
| UT-08 | FR-4.2 | RekognitionService creates/deletes collections, searches faces | pytest | Team | Yes | Yes | [`backend/tests/test_recognition.py` — TestRekognitionService](https://github.com/ailijevs/memento/blob/main/backend/tests/test_recognition.py) |
| IT-01 | FR-4.1 | /recognition/detect endpoint returns ProfileCards end-to-end | pytest | Marty | Yes | Yes | [`backend/tests/test_recognition.py` — TestDetectEndpoint](https://github.com/ailijevs/memento/blob/main/backend/tests/test_recognition.py) |
| IT-02 | FR-2.1 | Resume file type validation rejects unsupported formats | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestResumeParserFileType](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| IT-03 | FR-2.1 | Resume upload endpoint returns all fields (TestClient integration) | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestResumeUploadEndpoint](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| MT-01 | FR-2.1 | Resume upload populates all profile fields in Supabase | Manual | Marty | No | N/A | [`docs/testing/manual-reports/manual-test-report-001.md`](manual-reports/manual-test-report-001.md) |
| MT-02 | FR-4.1 | Recognition endpoint returns ProfileCard data for known face | Manual | Marty | No | N/A | [`docs/testing/manual-reports/manual-test-report-002.md`](manual-reports/manual-test-report-002.md) |
| UAT-01 | FR-2.1, FR-2.3 | End-to-end resume upload onboarding user acceptance test | Manual | Marty | No | N/A | [`docs/testing/manual-reports/manual-test-report-003-uat.md`](manual-reports/manual-test-report-003-uat.md) |

### Legend

- **UT** – Unit test
- **IT** – Integration test
- **MT** – Manual test
- **FR** – Functional requirement (per RVTM)

### Owner Key

- **Marty** – Tests authored or significantly modified by Marty
- **Team** – Shared ownership across team members
