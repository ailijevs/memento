# Manual Test Report #005

| Field | Value |
|-------|-------|
| **Report ID** | MT-005 |
| **Date** | 2026-03-15 |
| **Tester** | noddiemgbodille |
| **Test Case ID** | MT-05 |
| **Requirement ID** | FR-WebSocket-Realtime-Recognition |

---

## Test Steps

1. Start WebSocket server (`glasses-app` backend, expected on `ws://localhost:8080`).
2. Start frontend app and confirm `NEXT_PUBLIC_WS_URL` is set correctly (or defaults to `ws://localhost:8080`).
3. Open dashboard/recognition page and verify initial socket connection event.
4. Send `start_recognition` message from UI action; verify outbound payload and server `ack`.
5. Validate handling of `recognition_status` and `recognition_result` messages:
   - card list updates
   - timestamp ordering
   - duplicate profile merge behavior
6. Send `stop_recognition`; verify recognition loop halts and UI state updates.
7. Network interruption test:
   - stop WebSocket server while UI is open
   - verify disconnect warning appears and app does not crash
8. Invalid payload test:
   - send malformed JSON / unknown message type from test client
   - verify parser rejection and error logging without UI crash
9. Reconnect test:
   - restart server and reconnect from UI
   - verify recognition can restart cleanly.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Client connects and receives `connected`/`ack` style handshake messages | _Fill in after run_ | _TBD_ |
| `start_recognition` and `stop_recognition` correctly control stream state | _Fill in after run_ | _TBD_ |
| Recognition results render and update consistently in dashboard | _Fill in after run_ | _TBD_ |
| Disconnects and malformed messages do not crash frontend | _Fill in after run_ | _TBD_ |
| Reconnection restores functional recognition flow | _Fill in after run_ | _TBD_ |

---

## Outcome

- [ ] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- Browser console logs (`Connected`, `Disconnected`, error handling).
- WebSocket server logs for received message types.
- Screen capture of recognition feed before/after reconnect.
- Optional packet capture from browser DevTools Network > WS frames.

---

## Next Steps

1. Add auto-reconnect backoff if current reconnect behavior is manual-only.
2. Add structured telemetry for socket disconnect reasons.
3. Add automated contract tests for allowed message types.
