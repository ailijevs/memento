# Manual Test Report #002

| Field | Value |
|-------|-------|
| **Report ID** | MT-002 |
| **Date** | 2026-03-15 |
| **Tester** | Noddie Mgbodille |
| **Test Case ID** | MT-02 |
| **Requirement ID** | FR-Recognition-Storage (S3 image persistence) |

---

## Test Steps

1. Confirm AWS credentials and region used by backend are set (`AWS_REGION`, access key/secret, bucket env var).
2. Verify target bucket exists and is reachable:
   - `aws s3api head-bucket --bucket <bucket-name>`
3. Start backend locally:
   - `cd backend && uvicorn app.main:app --reload`
4. Trigger image upload path used by recognition flow (via app UI or API route that writes to S3).
5. Validate uploaded object appears in expected key prefix:
   - `aws s3 ls s3://<bucket-name>/<prefix>/ --recursive | tail`
6. Attempt retrieval using expected access path (presigned URL or backend retrieval endpoint).
7. Negative test: intentionally use invalid bucket name in env and repeat upload; verify graceful failure and useful error message.
8. Negative test: use unsupported file type or oversized payload and verify request validation behavior.
9. Validate logs for request ID, bucket, key, and failure reason if upload fails.

---

## Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Bucket connectivity check succeeds for configured bucket | _Fill in after run_ | _TBD_ |
| Upload returns success and stores object in expected key path | _Fill in after run_ | _TBD_ |
| Retrieval/presigned access works for uploaded object | _Fill in after run_ | _TBD_ |
| Invalid bucket configuration fails with actionable error | _Fill in after run_ | _TBD_ |
| Validation errors returned for invalid file payloads | _Fill in after run_ | _TBD_ |

---

## Outcome

- [ ] **Pass**
- [ ] **Fail**

---

## Logs / Screenshots / Evidence

```bash
# Bucket health check
aws s3api head-bucket --bucket <bucket-name>

# Verify recent uploads
aws s3 ls s3://<bucket-name>/<prefix>/ --recursive | tail -n 20
```

- Backend logs showing upload success/failure paths.
- Screenshot or log snippet of object key created.
- Evidence of negative test response bodies.

---

## Next Steps

1. If failures occur, add integration tests that mock S3 and cover failed upload/retrieval paths.
2. Add alerting for sustained S3 upload failure rates.
3. Document bucket policy/KMS requirements near deployment docs.
