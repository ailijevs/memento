# Manual Test Report #004

| Field | Value |
|-------|-------|
| **Report ID** | MT-004 |
| **Date** | 2026-03-15 |
| **Tester** | noddiemgbodille |
| **Test Case ID** | MT-04 |
| **Requirement ID** | FR-Event-Cleanup-Lambda |

---

## Test Steps

1. Confirm workflow validation is active for Event Cleanup:
   - `.github/workflows/lambda-event-cleanup.yaml` has PR `validate` job.
2. In a test branch, add a dependency import in cleanup handler without updating requirements.
3. Open PR and confirm `validate` job fails import check.
4. Add required package to `backend/lambdas/event_cleanup/requirements.txt`.
5. Confirm PR validation passes after fix.
6. Merge to `main` and confirm deploy runs only after `validate`.
7. Invoke Lambda (`memento-event-cleanup`) with test payload:
   - `{"window_hours":24}`
8. Validate CloudWatch logs for cleanup lifecycle:
   - pending events identified
   - collection deletion attempted
   - cleanup status updated (`in_progress`, `completed` or `failed`)
9. Validate Lambda response fields and counts are consistent with seeded test data.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| PR check fails when dependency declaration is missing | _Fill in after run_ | _TBD_ |
| PR check passes once requirements are updated | _Fill in after run_ | _TBD_ |
| Deploy triggers only after merge to `main` and successful validate | _Fill in after run_ | _TBD_ |
| Cleanup Lambda processes eligible events and returns summary | _Fill in after run_ | _TBD_ |
| Failures are logged and status is set to `failed` for bad events | _Fill in after run_ | _TBD_ |

---

## Outcome

- [ ] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- PR check links (fail and pass states).
- Deploy run link.
- CloudWatch logs showing collection deletion behavior.

```bash
aws lambda invoke \
  --function-name memento-event-cleanup \
  --payload '{"window_hours":24}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/event-cleanup-output.json && cat /tmp/event-cleanup-output.json
```

---

## Next Steps

1. Add canary events in a staging environment to verify cleanup safely.
2. Add alerting for repeated cleanup failures.
3. Add regression checks for event state transitions in manual inventory.
