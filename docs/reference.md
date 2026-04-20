# Reference [Team 5]

## System Structure

| Component | Path | Responsibility | Dependencies |
| --- | --- | --- | --- |
| Web client | `frontend/` | Next.js app for onboarding, dashboard, recognition UI | Backend API, glasses websocket server |
| Mentra/glasses server | `glasses-app/` | Bidirectional bridge with Mentra glasses: receives frames/status and sends instructions/updates (start/stop/ack/errors/results) over websocket | Mentra OS SDK, backend recognition API |
| Proxy server (dev only) | `proxy/` | Development reverse-proxy for routing frontend/API/glasses endpoints during MentraOS testing or when a single host/server runs all apps | Frontend app, backend API, glasses server |
| API service | `backend/app/` | FastAPI service for auth, profiles, events, memberships, consents, recognition | Supabase, AWS Rekognition, S3, OpenAI/PDL/Exa |
| Background workers | `backend/lambdas/` | Event face indexing and collection cleanup | Supabase, AWS Rekognition, S3 |
| Data layer | `backend/app/dals/` | Table-level data access wrappers | Supabase PostgREST |
| Schema layer | `backend/app/schemas/` | Pydantic request/response contracts | FastAPI |

**Primary runtime flow**

| Flow | Entry point | Downstream systems |
| --- | --- | --- |
| Dev routing (optional) | `proxy/` | Development-only traffic routing for MentraOS tests or single-server deployments |
| Glasses stream/control | `ws://<glasses-server>` (`NEXT_PUBLIC_WS_URL`) | Bidirectional instructions/updates between web client and Mentra glasses via glasses server |
| Auth/session | Supabase SDK in frontend/Next runtime (`supabase.auth.getUser`, `supabase.auth.getSession`, `signInWithPassword`, `signUp`, `signInWithOAuth`) | Supabase Auth (direct from frontend; no frontend calls to `/api/v1/auth/*`) |
| Event/profile CRUD | `GET/POST/PATCH/DELETE /api/v1/{profiles,events,memberships,consents}` | Supabase Postgres + RLS |
| Recognition request | `POST /api/v1/recognition/detect` | Rekognition collection lookup + profile card assembly + optional S3 presigned URLs |
| Event indexing | `lambdas.event_indexer.handler.handler` | Rekognition `CreateCollection`/`IndexFaces` |
| Event cleanup | `lambdas.event_cleanup.handler.handler` | Rekognition `DeleteCollection` |

## Key APIs / Interfaces

### HTTP Interface (FastAPI)

Base URL: `http(s)://<host>/api/v1`  
Auth: `Authorization: Bearer <supabase_jwt>` required on all authenticated routes.

| Route | Method | Request body | Response |
| --- | --- | --- | --- |
| `/profiles/me` | `GET` | None | `ProfileResponse` |
| `/profiles/me` | `POST` | `ProfileCreate` | `ProfileResponse` |
| `/profiles/me` | `PATCH` | `ProfileUpdate` | `ProfileResponse` |
| `/profiles/me/completion` | `GET` | None | `ProfileCompletionResponse` |
| `/profiles/enrich-linkedin` | `POST` | `LinkedInEnrichmentRequest` | `LinkedInEnrichmentResponse` |
| `/profiles/onboard-from-linkedin-url` | `POST` | `LinkedInOnboardingRequest` | `LinkedInOnboardingResponse` |
| `/profiles/me/resume` | `POST` | multipart file upload | `ResumeParseResponse` |
| `/profiles/directory/{event_id}` | `GET` | Path `event_id` | `ProfileDirectoryEntry[]` |
| `/profiles/{user_id}` | `GET` | Path `user_id` | `ProfileResponse` |
| `/profiles/me` | `DELETE` | None | `204 No Content` |
| `/events/` | `GET` | None | `EventResponse[]` |
| `/events/` | `POST` | `EventCreate` | `EventResponse` |
| `/events/{event_id}` | `GET` | Path `event_id` | `EventResponse` |
| `/events/{event_id}` | `PATCH` | `EventUpdate` | `EventResponse` |
| `/events/{event_id}` | `DELETE` | Path `event_id` | `204 No Content` |
| `/memberships/` | `GET` | None | `MembershipResponse[]` |
| `/memberships/join` | `POST` | `MembershipCreate` | `MembershipResponse` |
| `/memberships/event/{event_id}` | `GET` | Path `event_id` | `MembershipResponse[]` |
| `/memberships/event/{event_id}/me` | `GET` | Path `event_id` | `MembershipResponse` |
| `/memberships/event/{event_id}/me` | `PATCH` | `MembershipUpdate` | `MembershipResponse` |
| `/memberships/event/{event_id}/check-in` | `POST` | Path `event_id` | `MembershipResponse` |
| `/memberships/event/{event_id}/leave` | `DELETE` | Path `event_id` | `204 No Content` |
| `/consents/` | `GET` | None | `ConsentResponse[]` |
| `/consents/event/{event_id}` | `GET` | Path `event_id` | `ConsentResponse` |
| `/consents/event/{event_id}` | `PATCH` | `ConsentUpdate` | `ConsentResponse` |
| `/consents/event/{event_id}/grant-all` | `POST` | Path `event_id` | `ConsentResponse` |
| `/consents/event/{event_id}/revoke-all` | `POST` | Path `event_id` | `ConsentResponse` |
| `/recognition/detect` | `POST` | `FrameDetectionRequest` | `FrameDetectionResponse` |

### Authentication Interface (Supabase SDK)

Frontend auth/session contract (no frontend calls to backend `/api/v1/auth/*` routes).

| Operation | Runtime location | SDK call | Purpose |
| --- | --- | --- | --- |
| Verify current user (middleware) | `frontend/src/proxy.ts` | `supabase.auth.getUser()` | Protect `/dashboard` and `/onboarding` routes |
| Verify current user (app layout) | `frontend/src/app/(app)/layout.tsx` | `supabase.auth.getUser()` | Server-side guard for authenticated app shell |
| Read active session | multiple app pages | `supabase.auth.getSession()` | Retrieve access token/session for API calls |
| Email/password login | `frontend/src/app/(auth)/login/page.tsx` | `supabase.auth.signInWithPassword()` | User sign-in |
| Signup | `frontend/src/app/(auth)/signup/page.tsx` | `supabase.auth.signUp()` | User account creation |
| OAuth login/signup | auth pages | `supabase.auth.signInWithOAuth()` | Social auth flow |
| OAuth callback exchange | `frontend/src/app/auth/callback/route.ts` | `supabase.auth.exchangeCodeForSession()` | Convert OAuth code to session |
| Sign out | dashboard/profile pages | `supabase.auth.signOut()` | End session |

### WebSocket Interface (Glasses App)

Client implementation: `frontend/src/lib/socket.ts`  
Default URL: `ws://localhost:3001` (overridable via `NEXT_PUBLIC_WS_URL`)

| Direction | Message type | Payload |
| --- | --- | --- |
| Client -> Server | `start_recognition` | `{ event_id?: string }` |
| Client -> Server | `stop_recognition` | `undefined` |
| Server -> Client | `connected` | `{ clientId: string }` |
| Server -> Client | `ack` | `{ receivedType: string }` |
| Server -> Client | `error` | `{ reason: string }` |
| Server -> Client | `recognition_status` | `{ status: string }` |
| Server -> Client | `recognition_error` | `{ message: string }` |
| Server -> Client | `recognition_result` | `{ timestamp: string, result: FrameDetectionResponse }` |

## Configuration

Source of truth: `backend/app/config.py` (`Settings` via pydantic-settings; `.env` loaded).

### Required

| Variable | Type | Used by |
| --- | --- | --- |
| `SUPABASE_URL` | string | API, lambdas, auth verification |
| `SUPABASE_ANON_KEY` | string | API auth flows and user-scoped clients |
| `SUPABASE_SERVICE_ROLE_KEY` | string | Admin Supabase operations, recognition path, lambdas |
| `SUPABASE_JWT_SECRET` | string | JWT verification |

### Optional / feature-gated

| Variable | Default | Used by |
| --- | --- | --- |
| `APP_NAME` | `Memento API` | FastAPI metadata and health response |
| `DEBUG` | `false` | App behavior toggles |
| `EXA_API_KEY` | `null` | LinkedIn enrichment path |
| `MENTRA_API_KEY` | `null` | Mentra integrations |
| `PDL_API_KEY` | `null` | LinkedIn enrichment provider |
| `OPENAI_API_KEY` | `null` | Resume parsing and profile summaries |
| `PROFILE_SUMMARY_PROVIDER` | `auto` | Summary generation backend (`auto|dspy|template`) |
| `PROFILE_SUMMARY_MODEL` | `openai/gpt-4o-mini` | Summary model selection |
| `AWS_REGION` | `us-east-2` | Rekognition/S3 |
| `S3_BUCKET_NAME` | `null` | Profile image upload + recognition photo URL signing |
| `AWS_ACCESS_KEY_ID` | `null` | Local/dev AWS auth when IAM role unavailable |
| `AWS_SECRET_ACCESS_KEY` | `null` | Local/dev AWS auth when IAM role unavailable |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` (client fallback) | Frontend API target |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:3001` (client fallback) | Frontend websocket target |

## DB Schemas

Baseline schema is defined in `backend/supabase/migrations/001_initial_schema.sql`; migrations `002`-`005` apply additive updates used by the current system.

### Enums

| Enum | Values |
| --- | --- |
| `membership_role` | `attendee`, `organizer`, `admin` |
| `event_processing_status` | `pending`, `in_progress`, `completed`, `failed` |

### Tables

| Table | Primary key | Columns |
| --- | --- | --- |
| `public.profiles` | `user_id` | `full_name`, `headline`, `bio`, `location`, `company`, `major`, `graduation_year`, `linkedin_url`, `photo_path`, `experiences` (`jsonb`), `education` (`jsonb`), `profile_one_liner`, `profile_summary`, `summary_provider`, `summary_updated_at`, `created_at`, `updated_at` |
| `public.events` | `event_id` | `name`, `starts_at`, `ends_at`, `location`, `is_active`, `created_by`, `indexing_status`, `cleanup_status`, `created_at` |
| `public.event_memberships` | `(event_id, user_id)` | `role`, `checked_in_at`, `created_at` |
| `public.event_consents` | `(event_id, user_id)` | `allow_profile_display`, `allow_recognition`, `consented_at`, `revoked_at`, `updated_at` |

### Functions / Triggers / Policies

| Object | Type | Behavior |
| --- | --- | --- |
| `public.set_updated_at()` | Trigger function | Sets `updated_at = now()` on update |
| `trg_profiles_updated_at` | Trigger | Auto-updates `profiles.updated_at` |
| `trg_event_consents_updated_at` | Trigger | Auto-updates `event_consents.updated_at` |
| `public.get_event_directory(p_event_id uuid)` | SQL function | Returns consented directory rows for an event |
| RLS policies (`profiles`, `events`, `event_memberships`, `event_consents`) | Row-level security | Enforces same-event and consent-aware access control |

### Storage

| Bucket | Public | Policies |
| --- | --- | --- |
| `profile-photos` (Supabase Storage) | `true` | Legacy/deprecated path from migration `005`; being phased out in favor of S3-backed `photo_path` keys |

### AWS Services

| Service | Used for | Where |
| --- | --- | --- |
| S3 | Canonical profile image object storage (`photo_path` as S3 object key) | `backend/app/services/s3.py`, recognition presign in `backend/app/api/recognition.py`, indexing in `backend/lambdas/event_indexer/handler.py` |
| Rekognition | Face collection lifecycle, face indexing, face search | `backend/app/services/rekognition.py`, `backend/app/api/recognition.py`, lambdas |
| EventBridge (or equivalent scheduler) | Triggering indexer/cleanup lambdas on schedule | Deployment/infra concern; not called directly in app code |

## Project Specific Section 1

### Recognition Contract

`POST /api/v1/recognition/detect`

| Field | Type | Notes |
| --- | --- | --- |
| `image_base64` | `string` | Required; base64-encoded frame |
| `event_id` | `UUID \| null` | Optional; if set, uses event-scoped collection `memento_event_{event_id}` |

| Response field | Type | Notes |
| --- | --- | --- |
| `matches` | `ProfileCard[]` | Zero or more recognized users |
| `processing_time_ms` | `number` | End-to-end backend processing latency |
| `event_id` | `UUID \| null` | Echoed event context |

| `ProfileCard` field | Type |
| --- | --- |
| `user_id` | `string` |
| `full_name` | `string` |
| `headline`, `company`, `photo_path`, `profile_one_liner` | `string \| null` |
| `face_similarity` | `number (0..100)` |
| `experience_similarity` | `number \| null` |
| `bio`, `location`, `major`, `linkedin_url`, `profile_summary` | `string \| null` |
| `graduation_year` | `number \| null` |
| `experiences`, `education` | `object[] \| null` |

### Recognition failure conditions

| Condition | HTTP status | Detail |
| --- | --- | --- |
| `event_id` not found/inaccessible | `404` | Event lookup failed |
| `event.indexing_status == in_progress` | `409` | Indexing still running |
| `event.indexing_status in {pending, failed}` | `409` | Event collection unavailable |
| Base64 decode failure | `400` | Invalid image payload |
| Rekognition service exception | `502` | Upstream recognition failure |

## Project Specific Section 2

### Event Indexing/Cleanup Jobs

| Job | Entry point | Default window | Status column |
| --- | --- | --- | --- |
| Event indexer | `lambdas.event_indexer.handler.handler` | `window_minutes=20` | `events.indexing_status` |
| Event cleanup | `lambdas.event_cleanup.handler.handler` | `window_hours=24` | `events.cleanup_status` |

### Indexer state machine

| Step | Transition |
| --- | --- |
| Select events | `is_active=true` and `indexing_status=pending` and `starts_at <= now + window` |
| Start processing | `indexing_status: pending -> in_progress` |
| Provision collection | Ensure Rekognition collection `memento_event_{event_id}` |
| Index faces | For consented users (`allow_recognition=true`) with profile `photo_path` |
| Success | `indexing_status: in_progress -> completed` |
| Failure | `indexing_status: in_progress -> failed` |

### Cleanup state machine

| Step | Transition |
| --- | --- |
| Select events | `is_active=true` and `cleanup_status=pending` and `ends_at <= now - window` |
| Start processing | `cleanup_status: pending -> in_progress` |
| Delete collection | Delete Rekognition collection `memento_event_{event_id}` |
| Success | `cleanup_status: in_progress -> completed` |
| Failure | `cleanup_status: in_progress -> failed` |
