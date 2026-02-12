# Blueee V2 Flask Brain

## Setup

1. Copy environment variables into `backend/.env`.
2. Install dependencies:
   ```bash
   cd backend/flask
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
   Keep the terminal activated in `.venv` whenever you run or test this Flask service.
3. Run the server:
   ```bash
   python app.py
   ```

## Endpoints

- `POST /ai` tool-call router
- `POST /traffic` Google Maps Grounding summary
- `POST /transcribe` speech_recognition (Google Web Speech via ffmpeg)

## Notes

- `ffmpeg` must be installed and available on PATH for audio conversion.

## Tool-call Examples

```json
{ "action": "open_app", "params": { "name": "vscode" } }
```

```json
{ "action": "summarize_pdf", "params": { "path": "D:/Blueee V2/docs/sample.pdf" } }
```
