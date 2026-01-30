# Memento - Project Context

> Facial recognition networking system for MentraOS smart glasses that helps professionals identify and connect with people at events.

## What This Project Does

1. **User enrolls** at an event → uploads profile photo → photo indexed in AWS Rekognition
2. **Smart glasses capture** someone's face at the event
3. **System recognizes** the face → returns matching profile with LinkedIn info
4. **User sees** the person's name, headline, and professional background in AR

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | FastAPI (Python 3.11+) | REST API |
| Database | Supabase (PostgreSQL) | User data, events, consents |
| Auth | Supabase Auth | JWT-based authentication |
| Storage | Supabase Storage | Profile photos |
| Face Recognition | AWS Rekognition | Face indexing and matching |
| Data Scraping | Exa.ai API | LinkedIn profile extraction |

## Project Structure

```
memento-1/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   │   ├── profiles.py   # GET/PUT user profiles
│   │   │   ├── events.py     # CRUD events
│   │   │   ├── memberships.py # Join/leave events
│   │   │   └── consents.py   # Privacy consent management
│   │   ├── auth/
│   │   │   └── dependencies.py # Auth middleware (get_current_user)
│   │   ├── dals/             # Data Access Layers (DB queries)
│   │   ├── db/
│   │   │   └── supabase.py   # Supabase client initialization
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── config.py         # Settings loaded from .env
│   │   └── main.py           # FastAPI app entry point
│   ├── data/
│   │   ├── classlist.json    # Test data: 36 students with LinkedIn info
│   │   ├── profile_images/   # 20 profile photos for testing
│   │   └── har_files/        # LinkedIn HAR captures (gitignored)
│   ├── scripts/
│   │   ├── seed_database.py           # Seeds Supabase with test users
│   │   ├── parse_linkedin_profiles.py # Extracts URLs from HAR files
│   │   └── scrape_linkedin_exa.py     # Fetches full profiles via Exa.ai
│   ├── supabase/
│   │   └── migrations/
│   │       └── 001_initial_schema.sql # Schema + RLS policies
│   ├── tests/
│   ├── requirements.txt
│   └── .env                  # Local config (gitignored)
├── docs/                     # Design docs, V&V plan (PDFs)
├── CLAUDE.md                 # This file
└── README.md
```

## Local Setup

```bash
# 1. Clone and enter backend
cd memento-1/backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template and fill in values
cp .env.example .env
# Edit .env with your Supabase credentials

# 5. Seed the database (optional - for test data)
python scripts/seed_database.py

# 6. Run the server
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## Database Schema

### Tables

```
profiles
├── user_id (PK, FK → auth.users)
├── full_name
├── headline
├── bio
├── company
├── linkedin_url
├── photo_path (Supabase Storage URL)
└── created_at, updated_at

events
├── event_id (PK)
├── name
├── starts_at, ends_at
├── location
├── is_active
└── created_by (FK → auth.users)

event_memberships
├── (event_id, user_id) (PK)
├── role (attendee | organizer | admin)
└── checked_in_at

event_consents
├── (event_id, user_id) (PK)
├── allow_profile_display (boolean)
├── allow_recognition (boolean)
└── consented_at, revoked_at
```

### Row-Level Security (RLS)

**Critical privacy rule**: A user can only see another user's profile if:
1. They share at least one event membership, AND
2. The target user has `allow_profile_display = true` for that event

This is enforced at the database level - the API cannot bypass it.

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/profiles/me` | Get current user's profile |
| PUT | `/profiles/me` | Update current user's profile |
| GET | `/profiles/{user_id}` | Get another user's profile (RLS enforced) |
| GET | `/events` | List events user is member of |
| POST | `/events` | Create new event |
| POST | `/events/{id}/join` | Join an event |
| GET | `/events/{id}/members` | List event members |
| PUT | `/consents/{event_id}` | Update consent settings |
| POST | `/recognize` | **(TODO)** Submit image, get matching profiles |

## Environment Variables

```bash
# backend/.env

# Supabase (required)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-jwt-secret

# Optional
EXA_API_KEY=xxx  # For LinkedIn scraping scripts
DEBUG=false
```

**Never commit `.env`** - it contains secrets. Use `.env.example` as template.

## Data Flow

### Recognition Flow (Target State)
```
Smart Glasses → Image → /recognize endpoint
                            ↓
                    AWS Rekognition searchFaces()
                            ↓
                    Returns FaceId matches
                            ↓
                    Look up user_id from FaceId
                            ↓
                    Fetch profile (RLS checks consent)
                            ↓
                    Return profile to glasses
```

### Test Data Pipeline (Current)
```
LinkedIn Profile → HAR file capture → parse_linkedin_profiles.py
                                              ↓
                                      Extract LinkedIn URL
                                              ↓
                                      scrape_linkedin_exa.py
                                              ↓
                                      Fetch headline, experience, education
                                              ↓
                                      Update classlist.json
                                              ↓
                                      seed_database.py
                                              ↓
                                      Supabase (profiles + Storage)
```

## Scripts Reference

### seed_database.py
Creates test users in Supabase from `classlist.json`. Only seeds users who have `photo_path`.
```bash
python scripts/seed_database.py
```
- Creates users in Supabase Auth
- Uploads photos to Storage bucket `profile-photos`
- Creates profiles with LinkedIn data
- Creates test event "ECE 495 Spring 2026 Demo"
- Adds all users as members with consent enabled

### parse_linkedin_profiles.py
Extracts LinkedIn URLs from HAR files (browser network captures).
```bash
python scripts/parse_linkedin_profiles.py data/har_files
```
- Parses HAR files named `{Person Name}.har`
- Extracts LinkedIn profile URL from network requests
- Updates `classlist.json` with `linkedin_url`

### scrape_linkedin_exa.py
Fetches full profile data from LinkedIn via Exa.ai API.
```bash
python scripts/scrape_linkedin_exa.py --update-classlist
```
- Reads LinkedIn URLs from `classlist.json`
- Calls Exa.ai to get profile content
- Extracts headline, experience, education
- Updates `classlist.json` with scraped data

## Current Status

### Completed ✅
- Supabase schema with RLS policies
- FastAPI project structure with routers
- LinkedIn data extraction pipeline
- Database seeding with 20 test users
- Profile photos uploaded to Storage
- 20 LinkedIn URLs, 8 with full experience data

### Blocked ⏳
- AWS Rekognition access (waiting on approval)

### TODO 📋
- Issue #41: Collect LinkedIn data for remaining 16 people
- Issue #7: Create Rekognition collection per event
- Issue #8: Implement face enrollment endpoint
- Issue #9: Implement recognition endpoint

## Code Conventions

- **Routers**: One file per resource in `app/api/`
- **DALs**: Database queries isolated in `app/dals/`
- **Schemas**: Pydantic models for request/response validation
- **Auth**: Use `get_current_user` dependency for protected routes
- **Errors**: Raise `HTTPException` with appropriate status codes
- **Tests**: pytest with 80%+ coverage target

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes, then
git add .
git commit -m "Descriptive message"
git push -u origin feature/your-feature

# Create PR on GitHub
```

### Branches
- `main` - Production-ready, protected
- `feature_linkedin_parsing` - LinkedIn scraping (active)
- Create `feature/xxx` branches for new work

## Troubleshooting

### "Extra inputs are not permitted" error
Add new env vars to `app/config.py` Settings class.

### Supabase connection fails
Check `.env` has correct `SUPABASE_URL` and keys (should start with `eyJ`).

### HAR parser returns wrong profile
It might extract the logged-in user instead of visited profile. The parser uses the HAR filename as a hint - name files like `{Person Name}.har`.

### Exa.ai returns no results
Some LinkedIn profiles are private or not indexed. Try the Playwright scraper as fallback.

## Useful Links

- [Supabase Dashboard](https://supabase.com/dashboard)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [AWS Rekognition Docs](https://docs.aws.amazon.com/rekognition/)
- [GitHub Project Board](https://github.com/users/ailijevs/projects/1)
