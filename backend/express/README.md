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

## Endpoints

- `GET /health`
- `POST /api/voice`
- `GET /api/session`
- `POST /api/session`
- `GET /api/oauth/google/url`
- `GET /api/oauth/google/callback`
- `GET /api/oauth/google/tokens`

## WebSocket

- `ws://localhost:3001/audio`
