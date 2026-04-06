# Manual Test Report #009

| Field | Value |
|-------|-------|
| **Report ID** | MT-009 |
| **Date** | 2026-04-03 |
| **Tester** | Will Ott |
| **Test Case ID** | MT-09 |
| **Requirement ID** | FR-1.1, FR-4.1 |

---

### Test Steps

0. Start all services
    - frontend: npm run dev
    - glasses-app: npm run dev (or start command your team uses)
    - backend: uvicorn app.main:app --reload

1. Prepare envs
    - Frontend has correct NEXT_PUBLIC_WS_URL and API URL.
    - glasses-app has:
        BACKEND_URL
        RECOGNITION_SERVICE_TOKEN (must match backend)
    - backend has:
        RECOGNITION_SERVICE_TOKEN (if enforcing service token)
        Supabase config so JWT verification works
2) Positive case (happy path)
    - Sign into frontend.
    - Open Recognition page and start scanning in glasses mode.
    - Expected:
        WS connects (no auth error in console)
        start_recognition message is sent
        backend returns 200 for /recognition/detect
        frontend receives recognition_result via WS
3) Negative auth cases (core of this test)
    - Run each as separate test and record observed UI + logs:

    - Invalid WS JWT (frontend session missing/invalid):
        Expected WS rejection (invalid_auth_token style), no recognition starts.

    - Missing/wrong service token (glasses-app env):
        WS may still connect, but backend call should fail with 401; frontend should get recognition error/no results.

    - Missing/invalid backend JWT path (if endpoint requires user JWT from caller):
        backend returns 401, and frontend should show failure behavior.

---

### Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Describe expected outcome | Describe observed outcome | Yes / No |

---

### Outcome

- [ ] **Pass**
- [ ] **Fail**

---

### Logs / Screenshots / Evidence

- Attach or link to logs, screenshots, or other evidence
- Example: `![Screenshot](path/to/screenshot.png)`
- Example: `[CI Log](https://...)`

---

### Next Steps (as required)

- If failed: what follow-up is needed?
- If passed: any regression or edge cases to add?
- Action items:

1. …
2. …
