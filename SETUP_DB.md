# Setup DB for Persistent Chat Memory

This document captures the DB plan for moving Blueee V2 chat memory from browser/session storage to persistent storage (ChatGPT-like behavior across sessions/devices).

## Current State (MVP)
- Browser `sessionStorage` keeps chat history per tab/session.
- Express session keeps short server-side history.
- Works for short-lived context, but not durable across devices/logins.

## Recommended DB
- **Primary choice:** PostgreSQL (durable, relational, easy querying, production-ready).
- **Optional companion:** Redis for short-lived cache/fast context reads.

## Minimal Schema
Use two tables:

```sql
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  text TEXT NOT NULL,
  metadata_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
  ON messages(conversation_id, created_at);
```

## Env Vars (Express backend)
Add to `backend/.env` or `backend/express/.env`:

```env
DATABASE_URL=postgres://postgres:postgres@localhost:5432/blueee
DB_SSL=false
```

## API Contract (target)
- Client sends `conversationId` + latest user message.
- Server loads last N messages (e.g., 20), builds model prompt, stores assistant response.

Suggested endpoints:
- `POST /api/conversations` -> create conversation
- `GET /api/conversations/:id/messages?limit=50` -> fetch history
- `POST /api/conversations/:id/messages` -> append user/assistant turn

## Migration from Current Session Memory
1. Keep existing `sessionStorage` + session flow as fallback.
2. On first DB-enabled request:
   - create conversation if missing,
   - upsert existing local/session history into `messages`.
3. After confirmation, make DB source-of-truth for history retrieval.

## Storage/Retention Guidance
- Keep full history in DB.
- For prompting, only fetch recent window (e.g., 20–40 turns).
- Optionally summarize older turns into periodic `system` memory notes.

## Why this fixes your issues
1. Assistant gets prior context reliably.
2. Each transcription is appended to same conversation, not treated as unrelated.
3. Follow-up questions resolve correctly using previous messages.
4. Scales beyond browser session limits.

## Next Implementation Step
Implement a small DB layer in `backend/express/src/services/`:
- `db.js` (pool/client)
- `conversationStore.js` (CRUD for conversations/messages)
- update `/api/voice` to read/write via `conversationId`.
