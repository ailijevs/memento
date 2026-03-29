# Manual Test Report #003

| Field | Value |
|-------|-------|
| **Report ID** | MT-003 |
| **Date** | 2026-03-15 |
| **Tester** | Noddie Mgbodille |
| **Test Case ID** | MT-03 |
| **Requirement ID** | FR-Event-Indexer-Lambda |

---

## Test Steps

1. Confirm workflow validation is active for Event Indexer:
   - `.github/workflows/lambda-event-indexer.yaml` has PR `validate` job.
2. In a test branch, add a new third-party import to `backend/lambdas/event_indexer/handler.py` without updating `requirements.txt`.
3. Open PR and verify `validate` job fails on import smoke test (`python -c "import handler"` in container).
4. Update `backend/lambdas/event_indexer/requirements.txt` with the missing dependency.
5. Re-run PR checks and verify `validate` now passes.
6. Merge PR into `main` and verify deploy job executes only after `validate` success.
7. Invoke Lambda (`memento-event-indexer`) with test payload:
   - `{"window_minutes":20}`
8. Confirm CloudWatch logs show processing lifecycle:
   - started
   - events found
   - per-event completion or failure handling
9. Validate returned payload includes `events_scanned`, `events_completed`, `events_failed`.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| PR check fails when imports are missing from requirements | _Fill in after run_ | _TBD_ |
| PR check passes once requirements are corrected | _Fill in after run_ | _TBD_ |
| Deployment runs only on push to `main` and after validation | _Fill in after run_ | _TBD_ |
| Lambda invocation succeeds and logs show normal indexing flow | _Fill in after run_ | _TBD_ |
| Lambda returns expected summary fields | _Fill in after run_ | _TBD_ |

---

## Outcome

- [ ] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

- Link to failed PR check (missing dependency scenario).
- Link to passing PR check after requirements fix.
- Link to successful deploy run on merge.
- CloudWatch log excerpts for Lambda invocation.

```bash
aws lambda invoke \
  --function-name memento-event-indexer \
  --payload '{"window_minutes":20}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/event-indexer-output.json && cat /tmp/event-indexer-output.json
```

---

## Next Steps

1. Add a scheduled smoke invocation in non-prod to detect runtime regressions early.
2. Add alert thresholds for repeated indexing failures.
3. Add regression test case in test inventory for dependency drift.
