# How-To Memento

---

## End users

### How to sign in to the web app

**Purpose:** Access your profile, events, and recognition features tied to your account.

**Preconditions:** You have a Supabase account (or OAuth provider) enabled for this project’s frontend.

**Steps:**

1. Open the Memento frontend URL your team provides (local or deployed).
2. Use **Sign in** / **Sign up** and complete authentication (email/password or OAuth, depending on configuration).
3. Wait until you reach the app shell (e.g. dashboard or onboarding), confirming the session loaded.

**Expected result:** You are logged in; protected routes load without redirecting to the login page.

---

### How to join an event and set privacy for recognition

**Purpose:** Allow your profile to appear in the event directory and participate in face recognition only where you consent.

**Preconditions:** An event exists; you can join it (invite link, in-app join, or organizer adds you—per your deployment).

**Steps:**

1. Sign in and navigate to the **event** you want to join (or accept an invitation).
2. **Join** the event if you are not already a member.
3. Open **consent** / **privacy** settings for that event (wording may vary in the UI).
4. Enable **allow profile display** if you want others to see your profile in that event context.
5. Enable **allow recognition** if you agree to your face being used for recognition for that event.

**Expected result:** Your membership and consent rows are saved; recognition and directory features can apply subject to backend rules.

---

### How to test recognition using the phone camera on the dashboard

**Purpose:** Send live camera frames to the backend recognition endpoint without Mentra glasses.

**Preconditions:** Backend and frontend are running with correct URLs; you are logged in; recognition is configured for your environment.

**Steps:**

1. Start the backend API (your team’s documented URL).
2. Start the frontend and sign in.
3. Open the **dashboard**.
4. Switch from **Glasses** to **Phone** camera mode (toggle in the UI).
5. Start capture and point the camera at a subject; wait for recognition cycles to run.

**Expected result:** Recognition results may appear in the dashboard when faces match enrolled users and policies allow; otherwise the UI may show no new matches (depends on indexing and consent).

---

### How to reset your password

**Purpose:** Regain access if you forgot your password (handled by Supabase Auth).

**Preconditions:** Your email is registered; password reset email is enabled in the Supabase project.

**Steps:**

1. On the login screen, choose **Forgot password** (or equivalent).
2. Enter the email associated with your account.
3. Open the reset link from email and set a new password.
4. Sign in with the new password.

**Expected result:** You can authenticate with the new password; old password no longer works.

---

## Developers

### How to set up the backend development environment

**Purpose:** Run the FastAPI API locally with dependencies isolated in a virtual environment.

**Preconditions:** Python 3.11+ (or version your team standardizes on); Git repo cloned.

**Steps:**

1. Open a terminal and `cd` to `backend/`.
2. Create a venv: `python -m venv venv` (or `py -3.12 -m venv venv`).
3. Activate: Windows `.\venv\Scripts\activate`; Unix `source venv/bin/activate`.
4. Install: `pip install -r requirements.txt`.
5. Copy `backend/.env.example` to `backend/.env` and fill values (see next guide).

**Expected result:** `python -c "import fastapi"` succeeds; you can run the app entrypoint without import errors.

---

### How to configure environment variables for local development

**Purpose:** Point the backend at Supabase, AWS, and optional services so features work end-to-end.

**Preconditions:** `backend/.env` exists; you have Supabase project credentials; AWS access if using Rekognition/S3.

**Steps:**

1. Set **Supabase**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` from the Supabase dashboard (API and JWT settings).
2. Set **AWS** (for recognition/indexing): `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`; set `S3_BUCKET_NAME` if profile photos and the event indexer use S3 keys.
3. If your branch uses recognition service auth: set `RECOGNITION_SERVICE_TOKEN` and send it as `Authorization: Bearer …` from internal clients.
4. Start the API from `backend/` so `.env` loads (or pass `--env-file` to uvicorn with a correct path).

**Expected result:** `GET /health` returns healthy; authenticated routes can reach Supabase; Rekognition calls use the intended region.

---

### How to call the recognition endpoint locally (e.g. Postman)

**Purpose:** Submit a test image as base64 and inspect `matches` without the glasses app.

**Preconditions:** Backend running; Rekognition collection populated for your test (event indexer or manual indexing); valid auth if your branch requires it.

**Steps:**

1. Encode a JPEG: `python scripts/encode_data_jpg_to_base64.py --input path/to/image.jpg` (from `backend/`), or paste base64 into a JSON file (default output: `backend/image_base64.txt`).
2. In Postman: **POST** `http://127.0.0.1:8000/api/v1/recognition/detect`.
3. Header: `Content-Type: application/json`. If required: `Authorization: Bearer <RECOGNITION_SERVICE_TOKEN>` or Supabase JWT per your implementation.
4. Body (raw JSON): `{ "image_base64": "<paste>", "event_id": "<uuid>" }` or `"event_id": null` for the default collection name in code.

**Expected result:** **200** with `matches` (possibly empty if no face match); **401** if auth missing/invalid; **4xx/502** for bad input or Rekognition errors per API behavior.

---

### How to populate Rekognition faces for an event (event indexer)

**Purpose:** Index attendee profile photos into `memento_event_<event_id>` so recognition can return matches.

**Preconditions:** `S3_BUCKET_NAME` set; profile `photo_path` keys exist in that bucket; `event_consents.allow_recognition` true for users to index; event meets indexer criteria (`indexing_status`, `starts_at` window—see `backend/lambdas/event_indexer/README.md`); AWS permissions for Rekognition and S3.

**Steps:**

1. Read `backend/lambdas/event_indexer/README.md` for the exact selection rules and env vars.
2. Configure the same `.env` the indexer uses (service role Supabase, S3 bucket, AWS region/credentials).
3. Run the handler locally as documented in that README (Python snippet invoking `handler`), or deploy and trigger the Lambda in AWS.
4. Verify in AWS Rekognition that collection `memento_event_<your-event-uuid>` has **FaceCount > 0**.

**Expected result:** Event `indexing_status` moves to completed (on success); recognition requests with that `event_id` can return non-empty `matches` when the image matches an indexed face and consent allows profile display.
