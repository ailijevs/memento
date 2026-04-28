# Memento Backend Tests

This directory contains automated unit and integration tests for the Memento API.

## Structure

- `test_main.py` – Tests for root and health endpoints
- `manual/` – Manual test reports (see `docs/verification/` for template and inventory)

## Running Tests

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

With coverage:

```bash
python -m pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=50
```

## Live Cloud Integration Tests

These opt-in tests use real AWS services. They are skipped unless the required
environment variables and seeded data are present.

Run all live tests:

```bash
cd backend
python -m pytest tests/test_live_* -m live -v --tb=short
```

Required setup:

- `tests/test_live_s3_integrations.py`
  - `S3_BUCKET_NAME`
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
- `tests/test_live_recognition_flow.py`
  - `MEMENTO_LIVE_RECOGNITION_IMAGE_PATH`
  - `MEMENTO_LIVE_RECOGNITION_EXPECTED_USER_ID`
  - `MEMENTO_LIVE_RECOGNITION_API_KEY` when recognition API key hashes are configured

The recognition test assumes the image points at a face already indexed in the
default Rekognition collection and that the matched user has a real profile in
Supabase.

## Verification Documentation

- [Verification Test Inventory](../../docs/verification/verification-test-inventory.md)
- [Manual Test Template](../../docs/verification/manual-test-template.md)

---

## Defect Reports & Root Cause Analyses

Issues containing bug reports or RCAs completed this semester:

| Issue # | Defect Name | Severity | RCA Included |
|---------|-------------|----------|--------------|
| #47 | Application startup fails when .env contains undefined variables | Medium | Yes |

*Update this table when new bug reports or RCAs are completed.*
