# Verification Test Inventory

> This table lists every test from the Requirements Verification Traceability Matrix (RVTM). Automated tests run in CI on every push and PR. Manual tests are documented in `docs/testing/manual-reports/`.

## Test Documentation Location

- **`docs/testing/`** – Verification Test Inventory, manual test template, manual test reports
- **`backend/tests/`** – Automated unit/integration tests (pytest)
- **`frontend/src/**/__tests__/`** – Automated frontend unit tests (Vitest + React Testing Library)
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
| UT-09 | FR-4.3 | CompatibilityService: shared field extraction, score calculation, conversation starters | pytest | Sasha | Yes | Yes | [`backend/tests/test_compatibility.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_compatibility.py) |
| UT-10 | FR-4.4 | SSRF URL validation blocks private IPs, loopback, non-HTTPS before image fetch | pytest | Sasha | Yes | Yes | [`backend/tests/test_profiles_ssrf.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_profiles_ssrf.py) |
| UT-11 | FR-3.2 | Event time guards block delete after start and leave after end | pytest | Noddie | Yes | Yes | [`backend/tests/test_event_time_guards.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_event_time_guards.py) |
| UT-12 | FR-Recognition-Storage | Profile photo upload URL, confirm flow, and signed photo URL handling behave correctly | pytest | Noddie | Yes | Yes | [`backend/tests/test_profile_photo_upload_url.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_profile_photo_upload_url.py) |
| UT-13 | FR-Privacy-Consent | Consent toggle behavior enforces event privacy and recognition side effects correctly | pytest | Noddie | Yes | Yes | [`backend/tests/test_consents_update.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_consents_update.py) |
| IT-01 | FR-4.1 | /recognition/detect endpoint returns ProfileCards end-to-end | pytest | Marty | Yes | Yes | [`backend/tests/test_recognition.py` — TestDetectEndpoint](https://github.com/ailijevs/memento/blob/main/backend/tests/test_recognition.py) |
| IT-02 | FR-2.1 | Resume file type validation rejects unsupported formats | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestResumeParserFileType](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| IT-03 | FR-2.1 | Resume upload endpoint returns all fields (TestClient integration) | pytest | Marty | Yes | Yes | [`backend/tests/test_resume_parser.py` — TestResumeUploadEndpoint](https://github.com/ailijevs/memento/blob/main/backend/tests/test_resume_parser.py) |
| IT-04 | FR-Recognition-Storage | Live S3 integration verifies backend-generated upload URL, object upload, and confirm flow against a real bucket | pytest | Noddie | Yes | No | [`backend/tests/test_live_s3_integrations.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_live_s3_integrations.py) |
| IT-05 | FR-4.1 | Live recognition integration verifies `/recognition/detect` returns a seeded profile match from real infrastructure | pytest | Noddie | Yes | No | [`backend/tests/test_live_recognition_flow.py`](https://github.com/ailijevs/memento/blob/main/backend/tests/test_live_recognition_flow.py) |
| MT-01 | FR-2.1 | Resume upload populates all profile fields in Supabase | Manual | Marty | No | N/A | [`docs/testing/manual-reports/manual-test-report-001.md`](manual-reports/manual-test-report-001.md) |
| MT-02 | FR-Recognition-Storage | S3 image persistence | AWS CLI + Manual API/UI | Noddie | Partial | No | [`docs/testing/manual-reports/manual-test-report-002.md`](manual-reports/manual-test-report-002.md) |
| MT-03 | FR-Event-Indexer-Lambda | Event indexer Lambda deployment | GitHub Actions + AWS Lambda + CloudWatch | Team | Partial | Partial (validation in CI) | [`docs/testing/manual-reports/manual-test-report-003.md`](manual-reports/manual-test-report-003.md) |
| MT-04 | FR-Event-Cleanup-Lambda | Event cleanup Lambda deployment | GitHub Actions + AWS Lambda + CloudWatch | Team | Partial | Partial (validation in CI) | [`docs/testing/manual-reports/manual-test-report-004.md`](manual-reports/manual-test-report-004.md) |
| MT-05 | FR-WebSocket-Realtime-Recognition | WebSocket real-time recognition | Browser DevTools + WebSocket server logs | Team | No | No | [`docs/testing/manual-reports/manual-test-report-005.md`](manual-reports/manual-test-report-005.md) |
| MT-06 | FR-MentraOS-End-to-End-Recognition | MentraOS end-to-end recognition | MentraOS device/webview + proxy logs | Team | No | No | [`docs/testing/manual-reports/manual-test-report-006.md`](manual-reports/manual-test-report-006.md) |
| MT-08 | FR-4.1 | Recognition endpoint returns ProfileCard data for known face | Manual | Marty | No | N/A | [`docs/testing/manual-reports/manual-test-report-008.md`](manual-reports/manual-test-report-008.md) |
| MT-09 | FR-3.1, FR-3.2 | External-user manual testing of event CRUD and membership flow | Manual | Noddie | No | N/A | [`docs/testing/manual-reports/manual-test-report-009.md`](manual-reports/manual-test-report-009.md) |
| MT-10 | FR-Privacy-Consent, FR-4.1 | External-user manual testing of consent toggle flow and privacy behavior | Manual | Noddie | No | N/A | [`docs/testing/manual-reports/manual-test-report-010.md`](manual-reports/manual-test-report-010.md) |
| MT-11 | FR-Privacy-Consent, UX-Privacy-Clarity | External-user manual validation that privacy rules are clearly explained in the UI | Manual | Noddie | No | N/A | [`docs/testing/manual-reports/manual-test-report-011.md`](manual-reports/manual-test-report-011.md) |
| MT-12 | FR-Recognition-Storage | Manual integration testing of profile photo upload, replacement, and retrieval flow | Manual | Noddie | No | N/A | [`docs/testing/manual-reports/manual-test-report-012.md`](manual-reports/manual-test-report-012.md) |
| UAT-01 | FR-2.1, FR-2.3 | End-to-end resume upload onboarding user acceptance test | Manual | Marty | No | N/A | [`docs/testing/manual-reports/manual-test-report-003-uat.md`](manual-reports/manual-test-report-003-uat.md) |
| FE-UT-01 | FR-3.2 | Frontend component tests: ConfirmationDialog, BottomTabBar, ModalBottomSheet, LoginContent, SignupContent (50 tests) | Vitest | Marty | Yes | Yes | [`frontend/src/components/__tests__/`](https://github.com/ailijevs/memento/tree/main/frontend/src/components/__tests__) |
| FE-UT-02 | FR-3.2 | Frontend library tests: API client, consent cache, onboarding helpers, WebSocket client (54 tests) | Vitest | Marty | Yes | Yes | [`frontend/src/lib/__tests__/`](https://github.com/ailijevs/memento/tree/main/frontend/src/lib/__tests__) |
| FE-UT-03 | FR-3.3 | Dashboard page tests: loading, event list, tab switching, sign out, empty state (10 tests) | Vitest | Marty | Yes | Yes | [`frontend/src/app/(app)/dashboard/__tests__/dashboard-page.test.tsx`](https://github.com/ailijevs/memento/blob/main/frontend/src/app/(app)/dashboard/__tests__/dashboard-page.test.tsx) |
| FE-UT-04 | FR-3.3 | Dashboard sub-component tests: AttendeeContent, OrganizerContent, CreateEventSheet, EventDetailSheet, EventConsentsSheet (51 tests) | Vitest | Marty | Yes | Yes | [`frontend/src/app/(app)/dashboard/__tests__/`](https://github.com/ailijevs/memento/tree/main/frontend/src/app/(app)/dashboard/__tests__) |
| FE-UT-05 | FR-4.1 | Recognition page tests: loading, card rendering, camera toggle, consent warnings, socket connection, compatibility scores (20 tests) | Vitest | Marty | Yes | Yes | [`frontend/src/app/(app)/recognition/__tests__/recognition-page.test.tsx`](https://github.com/ailijevs/memento/blob/main/frontend/src/app/(app)/recognition/__tests__/recognition-page.test.tsx) |
| FE-UT-06 | FR-2.1 | Profile and onboarding page tests: profile rendering, sign out, edit mode, user profile viewing, onboarding LinkedIn/resume flow (31 tests) | Vitest | Marty | Yes | Yes | [`frontend/src/app/(app)/profile/__tests__/`](https://github.com/ailijevs/memento/tree/main/frontend/src/app/(app)/profile/__tests__) |
| FE-IT-01 | FR-1.1 | SignupContent integration test: full sign-up lifecycle with mocked Supabase auth, error handling, email verification routing (9 tests) | Vitest | Marty | Yes | Yes | [`frontend/src/components/__tests__/signup-content.test.tsx`](https://github.com/ailijevs/memento/blob/main/frontend/src/components/__tests__/signup-content.test.tsx) |

### Legend

- **UT** – Backend unit test
- **FE-UT** – Frontend unit test
- **IT** – Backend integration test
- **FE-IT** – Frontend integration test
- **MT** – Manual test
- **FR** – Functional requirement (per RVTM)

### Owner Key

- **Marty** – Tests authored or significantly modified by Marty
- **Noddie** – Tests authored or significantly modified by Noddie
- **Sasha** – Tests authored or significantly modified by Sasha
- **Team** – Shared ownership across team members
