# Verification Test Inventory

## Test Documentation Location

- **`docs/testing/`** - Verification Test Inventory, manual test reports
- **`backend/tests/`** - Automated unit and integration tests; CI-gated via GitHub Actions

---

## Table 1 – Verification Test Inventory

| Test Case ID | RVTM TC | Requirement ID | Description | Tool | Automated? | CI Integrated? | Evidence Link |
|---|---|---|---|---|---|---|---|
| UT-01 | TC-5, TC-6 | ID-5, ID-6 | Unit tests for RekognitionService: face search, face indexing (S3 and bytes), face deletion, collection management, and multi-face frame detection | pytest | Yes | Yes | [test_recognition.py](https://github.com/ailijevs/memento/blob/feature/face-enrollment/backend/tests/test_recognition.py) |
| UT-02 | TC-3 | ID-3 | Unit tests for CompatibilityService: shared company/school/field extraction, score calculation (capped at 100), and template-based conversation starter generation | pytest | Yes | Yes | [test_compatibility.py](https://github.com/ailijevs/memento/blob/feature/face-enrollment/backend/tests/test_compatibility.py) |
| UT-03 | TC-4 | ID-4 | Unit tests for SSRF URL validation: blocks private IP ranges (RFC-1918), loopback (127.0.0.1, ::1, localhost), non-HTTPS schemes, and malformed inputs before any external image fetch | pytest | Yes | Yes | [test_profiles_ssrf.py](https://github.com/ailijevs/memento/blob/feature/face-enrollment/backend/tests/test_profiles_ssrf.py) |
| IT-01 | TC-5, TC-6 | ID-5, ID-6 | Integration tests for POST /api/v1/recognition/detect: exercises full HTTP stack (routing, request validation, event lookup, service dispatch) with mocked AWS and Supabase; verifies 200 with profile cards, 400 on bad image, 502 on Rekognition failure, and correct per-event collection selection | pytest + FastAPI TestClient | Yes | Yes | [test_recognition.py (TestDetectEndpoint)](https://github.com/ailijevs/memento/blob/feature/face-enrollment/backend/tests/test_recognition.py) |
| MT-01 | TC-2 | ID-2 | Manual test: API health check and availability (GET / and GET /health return correct structure and HTTP 200) | Manual / curl | No | No | [manual-test-report-001.md](manual-reports/manual-test-report-001.md) |
| MT-02 | TC-5 | ID-5 | Manual test: end-to-end recognition pipeline using MentraOS smart glasses against enrolled test users; verifies profile cards appear within 1 second and matched fields are correct | Manual / glasses hardware | No | No | In progress |

---

### Legend

- **UT** - Unit test
- **IT** - Integration test
- **MT** - Manual test
- **TC** - Test case from RVTM (V&V document)
- **ID** - Requirement ID from RVTM
