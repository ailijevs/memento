# Event Cleanup Lambda

Deletes AWS Rekognition face collections for events that ended long enough ago to be cleaned up.

## What It Does

The handler (`handler.py`) runs this flow:

1. Query events where:
   - `is_active = true`
   - `cleanup_status = pending`
   - `ends_at <= now - window_hours` (default: 24)
2. Set each event's `cleanup_status` to `in_progress`.
3. Delete the Rekognition collection:
   - `memento_event_{event_id}`
4. Set event status:
   - `completed` if deletion succeeds
   - `failed` if an exception occurs for that event

## Handler

- Module: `handler`
- Function: `handler`

## Runtime Dependencies

Install from:

```bash
pip install -r backend/lambdas/event_cleanup/requirements.txt
```

## Required Environment Variables

Read through `app.config.Settings`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY` (not used by this lambda directly, but present in shared config)
- `SUPABASE_JWT_SECRET` (not used by this lambda directly, but present in shared config)
- AWS credentials/region via environment or IAM role:
  - `AWS_REGION`
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (local dev)

For Lambda in AWS, prefer IAM role permissions instead of static keys.

## Local Invocation

From `backend/`:

```bash
python - <<'PY'
from lambdas.event_cleanup.handler import handler

result = handler({"window_hours": 24}, None)
print(result)
PY
```

## Packaging (Zip)

Example from repo root:

```bash
cd backend
rm -rf /tmp/event_cleanup_build
mkdir -p /tmp/event_cleanup_build

# Install lambda deps
pip install -r lambdas/event_cleanup/requirements.txt -t /tmp/event_cleanup_build

# Copy shared app code and lambda code
cp -R app /tmp/event_cleanup_build/
cp -R lambdas/event_cleanup /tmp/event_cleanup_build/lambdas/event_cleanup

cd /tmp/event_cleanup_build
zip -r event_cleanup.zip .
```

## Deploy (AWS CLI)

```bash
aws lambda update-function-code \
  --function-name <your-lambda-name> \
  --zip-file fileb:///tmp/event_cleanup_build/event_cleanup.zip
```

Set handler to:

`lambdas.event_cleanup.handler.handler`

## IAM Permissions

Minimum permissions needed by Lambda role:

- Rekognition:
  - `rekognition:DeleteCollection`
- Network/Secrets as needed for Supabase access
