# Explanation - Memento

## System Overview

Memento is a facial recognition networking system for smart glasses. At an event, a user wearing MentraOS glasses can look at another attendee and instantly see their name, professional headline, and background overlaid in their field of view, without asking "what's your name?"

The system is built around a core privacy constraint. **You can only be recognized by someone if you are both attending the same event and you have explicitly opted in to recognition for that event.** This constraint shapes most of the architecture.

There are four main components:

| Component | Technology | Role |
|---|---|---|
| Backend API | FastAPI (Python) | Profiles, events, memberships, consents, recognition |
| Frontend | Next.js + React | Onboarding, profile management, event directory |
| Glasses App | MentraOS SDK (Node.js) | Frame capture, recognition loop, AR display |
| Proxy Gateway | Express | Single entry point (development/demo only) |

External services:

| Service | Purpose |
|---|---|
| Supabase | PostgreSQL database, JWT auth, file storage |
| AWS Rekognition | Face indexing and matching |
| AWS S3 | Profile photo storage |
| AWS Lambda | Async face indexing and event cleanup |
| PDL / Exa.ai | LinkedIn profile enrichment |
| OpenAI | AI-generated profile summaries |

### Scalability

The system is designed to scale horizontally at each layer. The FastAPI backend is stateless and can run multiple instances behind a load balancer since all state lives in Supabase and AWS. Rekognition collections are isolated per event, so adding more events does not degrade recognition performance for existing ones. The Lambda-based face indexing pipeline scales automatically with AWS, and each Lambda invocation processes one event independently. The main scalability constraint is Supabase connection limits on the free tier, which would need to be addressed before a high-traffic production deployment.

---

## Architecture Diagrams

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                      User's Phone                    │
│  ┌──────────────────────────────────────────────┐   │
│  │         Next.js Frontend (Vercel)             │   │
│  │  Onboarding · Dashboard · Profile · Events   │   │
│  └──────────────────┬───────────────────────────┘   │
└─────────────────────│───────────────────────────────┘
                       │ HTTPS (REST + Auth)
┌─────────────────────▼───────────────────────────────┐
│             FastAPI Backend (Railway)                 │
│  profiles · events · memberships · consents          │
│  recognition · enrichment · completion               │
│            │              │                          │
│       Supabase         AWS SDK                       │
│  (Auth + DB + Storage)  (S3 + Rekognition)           │
└─────────────────────────────────────────────────────┘
           ▲                        ▲
           │ WebSocket              │ Scheduled
┌──────────┴───────────┐  ┌────────┴────────────────┐
│  MentraOS Glasses App │  │     AWS Lambda           │
│  - Frame capture      │  │  event_indexer           │
│  - Recognition loop   │  │  event_cleanup           │
│  - TTS feedback       │  └─────────────────────────┘
└──────────────────────┘
```

### Recognition Data Flow

```
Glasses camera captures frame
        ↓
RecognitionController (500ms loop)
        ↓
POST /api/v1/recognition/detect {image_base64, event_id}
        ↓
AWS Rekognition SearchFacesByImage()
        ↓
FaceMatch[] {face_id, similarity, confidence}
        ↓
ProfileCardBuilder fetches profile per match (RLS enforced)
        ↓
Check consent: allow_profile_display = true?
        ↓
Attach presigned S3 photo URLs
        ↓
FrameDetectionResponse {matches[], processing_time_ms}
        ↓
WebSocket to Frontend to AR display
```

### Face Indexing Flow (Async, Lambda)

```
User joins event and consents to recognition
        ↓
event_indexer Lambda runs on schedule (every 20 min)
        ↓
Find events with indexing_status = pending
        ↓
Create Rekognition collection: memento_event_{event_id}
        ↓
For each consented member, fetch photo from S3 and index face
        ↓
Store FaceId to user_id mapping
        ↓
Mark event indexing_status = completed
```

### LinkedIn Onboarding Flow

```
User enters LinkedIn URL
        ↓
POST /profiles/onboard-from-linkedin-url
        ↓
LinkedInEnrichmentService tries PDL, falls back to Exa.ai
        ↓
Normalize name, headline, bio, location, experiences, education
        ↓
ProfileImageService downloads avatar and normalizes to JPEG
        ↓
S3 upload photo and return object key
        ↓
DB upsert profile (name, headline, experiences, education, photo_path)
        ↓
ProfileCompletionService computes missing required fields
        ↓
Response with profile, completion_percentage, missing_fields
```

---

## Key Components

### Backend API (`backend/app/`)

The backend is organized around four resource areas.

**Profiles** handle CRUD for user profiles. The `/onboard-from-linkedin-url` endpoint drives the happy path by enriching, downloading a photo, upserting, and checking completion. The `/me/completion` endpoint tells the frontend which required fields are still missing.

**Events** handle creation and management. Events have a lifecycle where they are created, then indexing_status is set to pending, then the Lambda indexes faces, then indexing_status becomes completed and recognition goes live. After the event ends, cleanup_status drives the Lambda that deletes the Rekognition collection.

**Memberships** track who is in each event. Joining an event creates a membership record. RLS on the profiles table uses memberships to determine who can see whom.

**Consents** give each membership a paired record with two flags. `allow_profile_display` controls whether others can see your profile card, and `allow_recognition` controls whether your face gets indexed. Both default to false and the user must explicitly opt in.

**Recognition** is handled by the `/detect` endpoint, which receives a base64 frame from the glasses, calls Rekognition, and returns profile cards. The endpoint is stateless and all state lives in the Rekognition collection and the database.

### Authentication (`backend/app/auth/dependencies.py`)

All protected routes use the `get_current_user` FastAPI dependency. It extracts the `Authorization: Bearer <token>` header, reads the JWT header to determine the algorithm, decodes using `SUPABASE_JWT_SECRET` for HS256, or fetches the public key from Supabase's JWKS endpoint for ES256 and RS256. It then validates the audience and issuer and returns a `CurrentUser` object with the user's id, email, and raw token.

The raw token is forwarded to Supabase on every database query via `postgrest.auth(token)`. This causes Supabase to evaluate all RLS policies as that user, so `auth.uid()` inside policies resolves to the authenticated user's ID.

### Database and RLS (`supabase/migrations/`)

The privacy model is enforced at the database layer. The critical policy is on the `profiles` table:

```sql
-- You can see another user's profile only if:
-- 1. You share an event with them, AND
-- 2. They have allow_profile_display = true for that event
CREATE POLICY profiles_select_same_event ON profiles FOR SELECT
USING (
  auth.uid() = user_id
  OR EXISTS (
    SELECT 1 FROM event_memberships em1
    JOIN event_memberships em2 ON em1.event_id = em2.event_id
    JOIN event_consents ec ON ec.event_id = em1.event_id AND ec.user_id = profiles.user_id
    WHERE em1.user_id = auth.uid()
      AND em2.user_id = profiles.user_id
      AND ec.allow_profile_display = true
  )
);
```

This means the application layer cannot accidentally expose a profile. Even a buggy query will return no rows for a non-consenting user.

The `event_memberships` select policy is intentionally non-recursive (`user_id = auth.uid()` only) to avoid circular RLS evaluation, which PostgreSQL does not handle gracefully.

### AWS Rekognition Integration (`backend/app/services/rekognition.py`)

Rekognition stores face embeddings in collections. Memento creates one collection per event (`memento_event_{event_id}`). When a glasses frame arrives, `SearchFacesByImage()` is called with the raw frame bytes and Rekognition returns a list of `FaceMatch` objects, each with a `FaceId`, `Similarity` score, and `Confidence`. The backend then looks up which `user_id` maps to each `FaceId` and fetches profiles subject to RLS.

The Lambda handles bulk indexing rather than doing it at enrollment time. This decouples event setup from user enrollment so users can join and consent hours after the event is created, and the next Lambda run will pick them up.

### Glasses App (`glasses-app/src/`)

The glasses app extends MentraOS's `AppServer` base class, which handles authentication and session lifecycle with the glasses hardware. The `RecognitionController` runs a continuous loop:

```
while (isRunning):
    photo = await session.camera.requestPhoto()
    response = await backendClient.recognizeFrame(photo, eventId)
    socketServer.broadcast(response)
    if (soundEnabled): announce new names via TTS
    await sleep(500ms)  // 2 FPS
```

The `SocketServer` is a WebSocket server that allows the frontend (running in a browser or on the glasses display) to receive recognition results in real time without polling.

---

## Design Decisions

### Why Supabase instead of a raw PostgreSQL + ORM setup?

Supabase provides three things that would otherwise require significant custom infrastructure. These are JWT authentication with JWKS support, Row-Level Security enforced at query time, and file storage. The alternative of running a PostgreSQL instance, writing an auth service, and managing an S3-equivalent would take weeks to secure properly. The tradeoff is that Supabase's PostgREST interface has quirks around empty 204 responses and RLS recursion limitations that required specific handling in the DAL layer.

### Why AWS Rekognition instead of running a local model?

Facial recognition model training and hosting is a specialized problem. Rekognition is a managed service that handles model quality, hardware acceleration, and scaling. The per-face cost is acceptable for the event-scoped use case. The main tradeoff is vendor lock-in and the need for AWS approval to use the service, which has been a blocking issue during development.

### Why event-scoped Rekognition collections instead of a single global collection?

A single global collection would be cheaper and simpler. The event-scoped design was chosen for two reasons. First, privacy isolation means that if a user revokes consent for one event, only that event's collection needs to be updated. Second, recognition results are scoped so matching someone in collection A does not mean they are at event B. The cost is that each event requires a separate Rekognition collection and the Lambda must manage collection lifecycle from creation to deletion.

### Why async Lambda-based face indexing instead of indexing at enrollment time?

Rekognition indexing is slow (100-500ms per face) and could fail. If indexing were synchronous on the join/consent endpoint, a timeout or Rekognition outage would block users from joining events. The Lambda approach decouples these so users join and consent instantly while faces are indexed in the background. The tradeoff is a delay of up to 20 minutes before a newly enrolled user is recognizable.

### Why PDL with Exa.ai fallback instead of scraping LinkedIn directly?

LinkedIn actively blocks scraping and its Terms of Service prohibit it. PDL is a licensed data provider that aggregates professional profiles legally. Exa.ai is a search-based enrichment service that can find public profile data. The two-provider approach provides resilience where PDL covers most profiles and Exa.ai catches edge cases or profiles PDL does not have.

### Why store experiences and education as JSONB?

Work history and education are variable-length, nested structures. Normalizing them into relational tables would require multiple joins for every profile fetch and complicate the enrichment pipeline. JSONB lets the enrichment service return arbitrarily structured data that is stored and returned without transformation. The tradeoff is that JSONB fields are harder to query and index.

---

## Tradeoffs and Limitations

### Privacy model is per-event, not global

A user cannot set a global "never recognize me" preference. Consent is granted or revoked per event. This was a deliberate choice since different events have different expectations, but it means a user joining 10 events must manage 10 consent settings.

### Face indexing has up to a 20-minute delay

The Lambda runs on a 20-minute schedule. A user who joins an event and consents 2 minutes before the Lambda runs will be indexed. A user who consents 1 minute before may wait 19 minutes. This delay is invisible to the user and there is no real-time feedback when indexing completes.

### Recognition is one-directional at 2 FPS

The glasses capture 2 frames per second. In a crowded room, multiple faces may appear in a single frame, but each `SearchFacesByImage` call only searches for one face (the most prominent one Rekognition detects). Detecting and matching multiple faces in a single frame is a future extension.

### Cleanup is irreversible

When the cleanup Lambda deletes a Rekognition collection, face embeddings are permanently gone. There is no "restore event" capability. This is the correct behavior for privacy compliance (GDPR right to erasure) but means historical recognition data cannot be recovered.

### dspy-ai and pyiceberg are in requirements.txt but not in active use

As surfaced by the SBOM analysis, `dspy-ai` was added experimentally (likely for the profile summary feature prototype) and brings in 30+ transitive dependencies including ML libraries, an ORM stack, and `diskcache`. `pyiceberg` was never part of any active feature. Both should be removed before any production deployment.

### AWS Rekognition approval is pending

The Rekognition service requires AWS account approval for facial analysis features. As of the current state of the project, the recognition pipeline is implemented and tested but cannot be exercised end-to-end without live AWS credentials. All other flows (onboarding, events, consents, profiles) are fully functional.
