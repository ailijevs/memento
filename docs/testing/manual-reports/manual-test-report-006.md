# Manual Test Report #006

| Field | Value |
|-------|-------|
| **Report ID** | MT-006 |
| **Date** | 2026-03-15 |
| **Tester** | Noddie Mgbodille |
| **Test Case ID** | MT-06 |
| **Requirement ID** | FR-MentraOS-End-to-End-Recognition |

---

## Test Steps

1. Start all local services:
   - Frontend (`localhost:3000`)
   - Backend API (`localhost:8000`)
   - Mentra service (`localhost:3001`, if required by app flow)
   - WebSocket server (`localhost:8080`)
2. Start proxy gateway:
   - `cd proxy && npm install && node gateway.js`
   - confirm gateway on `http://localhost:3002`
3. Configure MentraOS app/webview to use the proxy base URL (`http://<host>:3002` or tunnel URL mapped to port 3002).
4. Authenticate user in MentraOS flow and verify API calls route through proxy endpoints:
   - `/api` -> backend API (`localhost:8000/api`)
   - `/ws` -> WebSocket (`localhost:8080`)
   - `/mentra` -> Mentra backend (`localhost:3001`)
5. Start recognition from MentraOS client and confirm live result cards appear.
6. Validate profile detail rendering, image loading, and fallback behavior for null fields.
7. Test negative path by stopping one downstream service (for example WebSocket); verify error messaging and graceful degradation.
8. Repeat flow on fresh app restart to verify session continuity and endpoint routing stability.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| MentraOS client can access app endpoints via proxy URL | _Fill in after run_ | _TBD_ |
| API, WebSocket, and Mentra routes are correctly forwarded by gateway | _Fill in after run_ | _TBD_ |
| Recognition workflow functions end-to-end in MentraOS environment | _Fill in after run_ | _TBD_ |
| Service outage is handled without unrecoverable client failure | _Fill in after run_ | _TBD_ |

---

## Outcome

- [ ] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- Proxy startup log: `Gateway running on port 3002`
- Proxy request logs (if middleware logging enabled)
- MentraOS/webview screenshots of recognition flow
- Browser/console logs showing route usage and failures

---

## Next Steps

1. Add a short runbook for local MentraOS testing with required ports/env vars.
2. Add health checks for each upstream route behind the proxy.
3. Consider secure tunnel (`https`) and origin restrictions for non-local testing.

### Why the Proxy Was Needed for Localhost Testing

- MentraOS runs outside the local browser context of your dev machine, so direct `localhost` references in app code can resolve to the device itself rather than your host services.
- The gateway on port `3002` provides one stable origin that multiplexes multiple local services (`/`, `/api`, `/ws`, `/mentra`) and avoids fragmented host/port configuration.
- Proxying also reduces cross-origin and mixed-route issues by presenting frontend/API/WebSocket traffic behind a single entry point during local integration testing.
