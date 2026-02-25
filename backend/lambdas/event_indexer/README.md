# Event Indexer Lambda

Indexes attendee profile photos into an AWS Rekognition face collection for events that are starting soon.

## What It Does

The handler (`handler.py`) runs this flow:

1. Query events where:
   - `is_active = true`
   - `indexing_status = pending`
   - `starts_at <= now + window_minutes` (default: 20)
2. Set each event's `indexing_status` to `in_progress`.
3. Ensure Rekognition collection exists:
   - `memento_event_{event_id}`
4. Fetch users in `event_consents` for that event with `allow_recognition = true`.
5. For each user:
   - load profile from `profiles`
   - skip if profile/photo is missing
   - call Rekognition `index_faces` using S3 object at `photo_path`
6. Set event status:
   - `completed` if event loop succeeds
   - `failed` if an exception occurs for that event

## Handler

- Module: `handler`
- Function: `handler`

## Runtime Dependencies

Install from:

```bash
pip install -r backend/lambdas/event_indexer/requirements.txt
```

## Required Environment Variables

Read through `app.config.Settings`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY` (not used by this lambda directly, but present in shared config)
- `SUPABASE_JWT_SECRET` (not used by this lambda directly, but present in shared config)
- `S3_BUCKET_NAME`
- AWS credentials/region via environment or IAM role:
  - `AWS_REGION`
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (local dev)

For Lambda in AWS, prefer IAM role permissions instead of static keys.

## Local Invocation

From `backend/`:

```bash
python - <<'PY'
from lambdas.event_indexer.handler import handler

result = handler({"window_minutes": 20}, None)
print(result)
PY
```

## Packaging (Zip)

Example from repo root:

```bash
cd backend
rm -rf /tmp/event_indexer_build
mkdir -p /tmp/event_indexer_build

# Install lambda deps
pip install -r lambdas/event_indexer/requirements.txt -t /tmp/event_indexer_build

# Copy shared app code and lambda code
cp -R app /tmp/event_indexer_build/
cp -R lambdas/event_indexer /tmp/event_indexer_build/lambdas/event_indexer

cd /tmp/event_indexer_build
zip -r event_indexer.zip .
```

## Deploy (AWS CLI)

```bash
aws lambda update-function-code \
  --function-name <your-lambda-name> \
  --zip-file fileb:///tmp/event_indexer_build/event_indexer.zip
```

Set handler to:

`lambdas.event_indexer.handler.handler`

## IAM Permissions

Minimum permissions needed by Lambda role:

- Rekognition:
  - `rekognition:CreateCollection`
  - `rekognition:IndexFaces`
- S3 (for Rekognition to access objects):
  - `s3:GetObject` on the profile image bucket
- Network/Secrets as needed for Supabase access

