# Memento

**ECE 49595 - Team 5 | Software Track | Spring 2026**

Memento enables professionals and students to know names and roles before conversations begin, leading to more confident introductions, efficient discussions, and stronger connections at networking events. Using facial recognition on MentraOS smart glasses, Memento identifies people at events and displays their profile information in real-time AR.

## Live Application

**Frontend (web app):** https://memento-4f4m.vercel.app

**Backend API:** https://memento-production-bb42.up.railway.app

**API Docs (Swagger):** https://memento-production-bb42.up.railway.app/docs

## Features

- Real-time facial recognition using smart glasses camera
- Profile display (name, major, headline, professional experiences)
- Compatibility scoring and conversation starter generation between attendees
- Event creation, discovery, and management (attendee and organizer views)
- Privacy-focused with explicit user consent and event-based access controls

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (React), deployed on Vercel |
| Backend | FastAPI (Python 3.11), deployed on Railway |
| WebSocket | Node.js glasses-app server, deployed on Railway |
| Database | Supabase (PostgreSQL + Auth + RLS) |
| Facial Recognition | AWS Rekognition |
| AI | OpenAI API + DSPy |
| Hardware | MentraOS Smart Glasses |

## Getting Started (Reviewer Access)

1. Navigate to https://memento-4f4m.vercel.app
2. Sign up with your email and password
3. Verify your email via the confirmation link sent to your inbox
4. Complete onboarding — enter your name, upload a profile photo, and fill in your professional details
5. From the dashboard, browse and join active events under the **Attendee** tab
6. Organizers can create and manage events under the **Organizer** tab

> Face recognition can be performed using either MentraOS smart glasses or your phone/laptop camera directly from the web app. Navigate to the **Recognition** tab on the dashboard and toggle between glasses and camera mode.

## Team

ECE 49595 – Team 5 (Software Track)

- Sasha Ilijevski
- Amartya Singh
- Noddie Mgbodille
- Will Ott

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your credentials
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # fill in your credentials
npm run dev
```

### Glasses App

```bash
cd glasses-app
npm install
cp .env.example .env  # fill in your credentials
npm start
```

See `backend/.env.example` and `glasses-app/.env.example` for required environment variables.
