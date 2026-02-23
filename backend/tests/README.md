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
