# Verification Test Inventory

> **Instructions:** This table must include every test from your RVTM (Requirements Verification Traceability Matrix). Cross-check with your V&V document and add tests based on feedback or new requirements. Keep this document updated throughout the semester.

## Test Documentation Location

Test documentation resides in:

- **`docs/verification/`** – Verification Test Inventory, manual test template, manual test reports
- **`backend/tests/`** – Automated unit/integration tests; README with defect/RCA tracking
- **`backend/tests/manual/`** – Manual test reports and evidence

This structure keeps V&V artifacts in `docs/verification/` while aligning with the backend-centric architecture of the project. Automated tests live next to the code they verify; manual test reports are grouped under `docs/verification/` for discoverability.

---

## Table 1 – Verification Test Inventory

| Test Case ID | Requirement ID | Tool | Automated? | CI Integrated? | Evidence Link | Frequency |
|--------------|----------------|------|------------|----------------|---------------|-----------|
| UT-01 | FR-3.1 | pytest | Yes | Yes | [GitHub Actions log](https://github.com/ailijevs/memento-1/actions) | Once per build |
| UT-02 | FR-3.1 | pytest | Yes | Yes | [GitHub Actions log](https://github.com/ailijevs/memento-1/actions) | Once per build |
| IT-01 | FR-1.x | pytest | Yes | Yes | [GitHub Actions log](https://github.com/ailijevs/memento-1/actions) | Once per build |
| MT-01 | FR-3.1 | Manual | No | N/A | [manual-test-report-001.md](manual-reports/manual-test-report-001.md) | Every two weeks |
| MT-02 | FR-Recognition-Storage | AWS CLI + Manual API/UI | Partial | No | [manual-test-report-002.md](manual-reports/manual-test-report-002.md) | Every two weeks |
| MT-03 | FR-Event-Indexer-Lambda | GitHub Actions + AWS Lambda + CloudWatch | Partial | Partial (validation in CI) | [manual-test-report-003.md](manual-reports/manual-test-report-003.md) | On Lambda workflow change |
| MT-04 | FR-Event-Cleanup-Lambda | GitHub Actions + AWS Lambda + CloudWatch | Partial | Partial (validation in CI) | [manual-test-report-004.md](manual-reports/manual-test-report-004.md) | On Lambda workflow change |
| MT-05 | FR-WebSocket-Realtime-Recognition | Browser DevTools + WebSocket server logs | No | No | [manual-test-report-005.md](manual-reports/manual-test-report-005.md) | Every two weeks |
| MT-06 | FR-MentraOS-End-to-End-Recognition | MentraOS device/webview + proxy logs | No | No | [manual-test-report-006.md](manual-reports/manual-test-report-006.md) | Before release |

### Legend

- **UT** – Unit test
- **IT** – Integration test
- **MT** – Manual test
- **FR** – Functional requirement (align with your RVTM)

### Notes

- Replace example rows above with your RVTM tests. Ensure every RVTM test is represented.
- For CI integration: if not yet complete, write "Not completed yet" and put the expected date in Evidence Link.
- For manual tests: put the expected date of first run in Evidence Link.
