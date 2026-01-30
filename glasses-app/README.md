# Memento Glasses App

MentraOS smart glasses app for face recognition.

## Setup

```bash
# Install dependencies
npm install

# Copy environment config
cp .env.example .env
# Edit .env with your API key

# Start the app
npm start

# Or with auto-reload for development
npm run dev
```

## How It Works

1. User wears smart glasses running MentraOS
2. User says "identify" or "who is this"
3. App captures photo from glasses camera
4. Photo sent to Memento backend `/recognize` endpoint
5. Backend uses AWS Rekognition to find matching profile
6. Profile info displayed on glasses

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MENTRA_API_KEY` | Your MentraOS developer API key |
| `BACKEND_URL` | URL of the Memento FastAPI backend |
| `PORT` | Port for the app server (default: 3000) |

## Testing Without Glasses

You can test the backend integration without actual glasses:

```bash
# The Mentra SDK has a simulator mode
# Or test the /recognize endpoint directly with curl
curl -X POST http://localhost:8000/recognize \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_encoded_image_here"}'
```

## Requirements

- Node.js 18+
- Memento backend running (FastAPI)
- AWS Rekognition configured (for face matching)
