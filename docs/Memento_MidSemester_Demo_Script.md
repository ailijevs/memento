# Memento Mid-Semester Demo — 5-Minute Script (4 Speakers)

**Total: ~5 min** · **Marty → Will → Noddie → Sasha** · **~75 sec each**

---

## MARTY — Slides 1–5

**Slide 1**  
Hey, we’re Team 5. This is Memento — real-time facial recognition for smart glasses. Quick mid-semester walkthrough for ECE 49595.

**Slide 2**  
The problem: you’re at a networking event, you see a face you know, and you blank on the name. We want context before you speak — hands-free on the glasses, consent-driven and event-scoped, so you get a real profile, not just a name.

**Slide 3**  
We’re building for students and pros at career fairs, event organizers who want smarter check-in, and anyone who’s ever blanked on a name.

**Slide 4**  
Stack in short: glasses talk to Mentra over WebSocket; frontend is Next.js and React, backend is FastAPI; Supabase for DB and auth, AWS for Rekognition and Lambdas, PDL and Exa for LinkedIn, OpenAI for summaries. It’s all wired up.

**Slide 5**  
In the app: welcome, sign in with email or Google, seven-step onboarding with LinkedIn or resume auto-fill, then dashboard with the recognition feed and capture toggle. Auth, onboarding, dashboard, and glasses sync are in. Will’s up next.

---

## WILL — Slides 6–10

**Slide 6**  
Frontend: auth, onboarding, profile, dashboard, and capture toggle are done. Event UI is partial — backend’s there, we’re still building the screens. For demos we use about 20 seeded users so we can run recognition end-to-end.

**Slide 7**  
Backend has six routers — profiles, events, consents, recognition detect, memberships, and a health check. Recognition takes a frame and returns the profile card after we check consent.

**Slide 8**  
Onboarding: user gives a LinkedIn URL or uploads a resume. We use PDL or Exa for LinkedIn; for resumes we use pdfplumber or python-docx, plus OCR for scans. We save to Postgres, run GPT-4o-mini for the one-liner and summary, and the frontend routes them to the next step or dashboard.

**Slide 9**  
Recognition: user taps scan, Mentra server tells the glasses to capture, we get the frame on our detect endpoint, run Rekognition, check consent, build the profile card, and push name and headline back over WebSocket. Full loop is working.

**Slide 10**  
We rely on Supabase, AWS Rekognition and Lambda, PDL and Exa, OpenAI, and the Mentra SDK. CI runs lint, tests, and Lambda builds to ECR with a 50% coverage bar. Noddie’ll cover how we test and enforce that.

---

## NODDIE — Slides 11–14

**Slide 11**  
API does standard CRUD — POST for profiles and events, GET with RLS for reads, PATCH and PUT for updates. Lambdas clean up Rekognition and S3 when events end; consent revokes are soft-deleted with revoked_at.

**Slide 12**  
Four main tables: profiles, events, memberships, consents. Privacy is in the database: you only see someone’s profile if you share an event and they’ve turned on display. So even with a bug in our code, Supabase won’t leak non-consenting users.

**Slide 13**  
We run pytest on every push and PR, 50% coverage minimum, plus pre-commit with black, isort, flake8, and mypy. Lambdas build in CI and push to ECR so infra is in the same pipeline as the app.

**Slide 14**  
We’ve walked the full flow by hand — onboard, join event, consent, index, scan, see the card. We’ve tested LinkedIn and OAuth and confirmed non-consenting users don’t show up. We’ve also run the glasses on real Mentra hardware. Sasha’s got the bugs we found and what’s next.

---

## SASHA — Slides 15–19

**Slide 15**  
We hit three big issues. One: profile card builder wasn’t checking consent — we fixed that in the builder and at the DB. Two: Supabase uses ES256 JWTs and we were verifying with the wrong key — we hooked up JWKS. Three: OAuth redirect was wrong behind the proxy — we set NEXT_PUBLIC_SITE_URL and the flow works now.

**Slide 16**  
What’s missing: no full event or consent UI yet, we’re local so there’s latency, LinkedIn depends on external APIs, and the glasses need the backend with no offline mode. That’s where we are.

**Slide 17**  
Next: weeks 9–10 event and consent UI; 10–11 more testing and WebSocket upgrades; 11–12 higher coverage and latency work; 12–14 final integration, physical demo, and production prep.

**Slide 18**  
That’s Memento, and thank you for watching

**Slide 19**  
Box link and contribution table are in the deck. Thanks.

---

## Timing

| Speaker | Slides | ~Time |
|--------|--------|-------|
| Marty  | 1–5    | 1:15  |
| Will   | 6–10   | 1:15  |
| Noddie | 11–14  | 1:15  |
| Sasha  | 15–19  | 1:15  |

Run through with the deck once so slide changes line up; trim or stretch a line or two per section to hit 5 min.
