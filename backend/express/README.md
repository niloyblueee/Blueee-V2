# Blueee V2 Gateway (Express)

## Setup

1. Copy environment variables into `backend/.env`.
2. Install dependencies:
   ```bash
   cd backend/express
   npm install
   ```
3. Start the server:
   ```bash
   npm run dev
   ```

## Real-time Features

Weather, time, and real-time queries are handled via:
- **Google Search Grounding** - Gemini uses Google Search to fetch current weather, news, etc.
- **Pattern-based time** - Local system time queries

No additional API keys needed beyond `GEMINI_API_KEY`.

## Endpoints

- `GET /health`
- `POST /api/voice` - Main voice assistant endpoint (handles weather, time, quick replies, thinking mode)
- `GET /api/session`
- `POST /api/session`
- `GET /api/oauth/google/url`
- `GET /api/oauth/google/callback`
- `GET /api/oauth/google/tokens`

## WebSocket

- `ws://localhost:3001/audio`
