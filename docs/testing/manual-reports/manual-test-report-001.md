# Manual Test Report #001

| Field | Value |
|-------|-------|
| **Report ID** | MT-001 |
| **Date** | 2026-02-07 |
| **Tester** | [Your name] |
| **Test Case ID** | MT-01 |
| **Requirement ID** | FR-3.1 (API availability / health checks) |

---

## Test Steps

1. Start the backend locally: `cd backend && uvicorn app.main:app --reload`
2. Open a browser or use `curl` to call `GET http://localhost:8000/`
3. Call `GET http://localhost:8000/health`
4. Verify response structure and values

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Root returns `{"status": "ok", "service": "Memento API"}` | `{"status": "ok", "service": "Memento API"}` | Yes |
| Health returns `{"status": "healthy", "service": "...", "version": "1.0.0"}` | `{"status": "healthy", "service": "Memento API", "version": "1.0.0"}` | Yes |
| HTTP 200 for both endpoints | 200 OK | Yes |

---

## Outcome

- [x] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

```bash
$ curl -s http://localhost:8000/
{"status":"ok","service":"Memento API"}

$ curl -s http://localhost:8000/health
{"status":"healthy","service":"Memento API","version":"1.0.0"}
```

---

## Next Steps

- No failures; no immediate action.
- Consider adding periodic health checks in production monitoring.
