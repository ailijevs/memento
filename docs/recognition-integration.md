# Recognition Integration Guide

This document describes how the real-time recognition pipeline works and how to integrate with it. The backend publishes face recognition results to a Supabase table, and the phone app subscribes via Supabase Realtime to display matches instantly.

## Architecture Overview

```
Smart Glasses (frame every ~300ms)
       |
       v
  POST /api/v1/recognize   <-- Rekognition peer builds this
       |
       v
  AWS Rekognition searchFaces()
       |
       v
  RecognitionPublisher.publish()   <-- inserts row
       |
       v
  recognition_results table   <-- Supabase Realtime broadcasts INSERT
       |
       v
  Phone app receives match   <-- Frontend peer subscribes here
```

## Database Schema

### recognition_results

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key, auto-generated |
| user_id | uuid | The glasses wearer who initiated recognition |
| event_id | uuid | The event where recognition occurred |
| matched_user_id | uuid (nullable) | The person identified in the frame, null if no match |
| confidence | float | Rekognition confidence score, 0.0 to 1.0 |
| created_at | timestamptz | When the recognition occurred |

### Row-Level Security

Users can only SELECT and DELETE their own rows (where `user_id = auth.uid()`). Only the backend service role can INSERT rows. This means end users cannot see other people's recognition activity or inject fake results.

### Data Retention

Rows are automatically cleaned up after 5 minutes via lazy cleanup (runs during publish calls) and a manual cleanup endpoint. Recognition data is ephemeral and should not be treated as persistent storage.

## For the Rekognition Peer

### Using RecognitionPublisher

After your `/recognize` endpoint processes a frame and gets a match from Rekognition, publish the result:

```python
from app.db.supabase import get_admin_client
from app.services.recognition_publisher import RecognitionPublisher

admin_client = get_admin_client()
publisher = RecognitionPublisher(admin_client)

# After Rekognition returns a match
publisher.publish(
    user_id=wearer_id,        # the authenticated user wearing glasses
    event_id=event_id,        # the event they are at
    matched_user_id=match_id, # the person identified (or None)
    confidence=0.93,          # Rekognition confidence score
)
```

### Method Signature

```python
def publish(
    self,
    *,
    user_id: str,          # required, glasses wearer UUID
    event_id: str,         # required, event UUID
    matched_user_id: str | None,  # None if no match found
    confidence: float,     # 0.0 to 1.0
) -> bool:                 # True if inserted, False if deduplicated or failed
```

### Deduplication Behavior

If the same `(user_id, matched_user_id)` pair is published within 2 seconds, the second call is silently skipped and returns `False`. This prevents the phone from being flooded with duplicate results when the glasses capture the same person across consecutive frames at ~300ms intervals.

Different `matched_user_id` values are always allowed regardless of timing.

### Error Handling

`publish()` never raises exceptions. If the database insert fails, it logs the error and returns `False`. This ensures a failed publish never crashes your recognition endpoint.

### Lazy Cleanup

The publisher automatically runs cleanup during `publish()` calls if more than 60 seconds have passed since the last cleanup. You do not need to manage cleanup yourself.

## For the Frontend Peer

### Subscribing to Recognition Results

Use the Supabase client to subscribe to INSERT events on the `recognition_results` table:

```typescript
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// Subscribe to recognition results for the current user and event
const channel = supabase
  .channel("recognition-feed")
  .on(
    "postgres_changes",
    {
      event: "INSERT",
      schema: "public",
      table: "recognition_results",
      filter: `user_id=eq.${currentUserId}`,
    },
    (payload) => {
      const result = payload.new;
      // result.matched_user_id - the person identified
      // result.confidence - match confidence (0.0-1.0)
      // result.event_id - the event context
      // result.created_at - when it happened

      if (result.matched_user_id) {
        // Fetch the matched person's profile and display it
        fetchProfile(result.matched_user_id);
      }
    }
  )
  .subscribe();

// Clean up when component unmounts
return () => {
  supabase.removeChannel(channel);
};
```

### Payload Format

When a new row is inserted, Supabase Realtime delivers a payload like:

```json
{
  "new": {
    "id": "a1b2c3d4-...",
    "user_id": "wearer-uuid",
    "event_id": "event-uuid",
    "matched_user_id": "matched-person-uuid",
    "confidence": 0.93,
    "created_at": "2026-02-01T18:30:00.000Z"
  }
}
```

### Authentication Requirements

The user must be authenticated with Supabase for the Realtime subscription to work. RLS ensures they only receive rows where `user_id` matches their own `auth.uid()`. No additional auth headers are needed beyond the standard Supabase session.

### Fetching the Matched Profile

After receiving a `matched_user_id`, fetch the profile using the existing API:

```typescript
const profile = await api.request(`/api/v1/profiles/${matchedUserId}`);
```

This respects RLS and consent rules. The profile will only be returned if both users share an event membership and the matched user has `allow_profile_display = true`.

## Cleanup Endpoint

### POST /api/v1/recognition/cleanup

Manually trigger cleanup of old recognition results. Requires authentication.

**Query Parameter:**
- `max_age_minutes` (int, default 5) — delete rows older than this

**Response:**
```json
{
  "deleted_count": 42,
  "max_age_minutes": 5
}
```

This endpoint is useful for cron jobs or manual maintenance. During normal operation, lazy cleanup handles this automatically.
