import json
import os
import subprocess
import tempfile
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
import psutil

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    import ctypes
    PYCAW_AVAILABLE = True
except Exception:
    PYCAW_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except Exception:
    GOOGLE_API_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except Exception:
    SPEECH_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = Flask(__name__)

print(f"[flask] speech_recognition available: {SPEECH_AVAILABLE}")
print(f"[flask] pyttsx3 available: {TTS_AVAILABLE}")

ALLOWED_HOSTS = {"127.0.0.1", "::1"}

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("gemini_api_key")

# Get workspace root (parent of backend folder)
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Get OAuth client secret path and resolve it relative to workspace root
oauth_path = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "backend/flask/client_secret.json")
if not os.path.isabs(oauth_path):
    # If relative path, resolve from workspace root
    GOOGLE_OAUTH_CLIENT_SECRET = os.path.join(WORKSPACE_ROOT, oauth_path)
else:
    GOOGLE_OAUTH_CLIENT_SECRET = oauth_path

print(f"[flask] Workspace root: {WORKSPACE_ROOT}")
print(f"[flask] Looking for OAuth client secret at: {GOOGLE_OAUTH_CLIENT_SECRET}")
print(f"[flask] OAuth file exists: {os.path.exists(GOOGLE_OAUTH_CLIENT_SECRET)}")

# Get token path and resolve it relative to workspace root
token_path = os.getenv("GOOGLE_TOKEN_PATH", "backend/flask/tokens.json")
if not os.path.isabs(token_path):
    # If relative path, resolve from workspace root
    GOOGLE_TOKEN_PATH = os.path.join(WORKSPACE_ROOT, token_path)
else:
    GOOGLE_TOKEN_PATH = token_path

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/youtube.readonly"
]

APP_COMMANDS = {
    "vscode": ["cmd", "/c", "code"],
    "chrome": ["cmd", "/c", "start", "chrome"],
    "edge": ["cmd", "/c", "start", "msedge"],
    "notepad": ["cmd", "/c", "start", "notepad"]
}

APP_PROCESS_MATCH = {
    "vscode": ["code.exe"],
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "notepad": ["notepad.exe"]
}


def ensure_localhost():
    if request.remote_addr not in ALLOWED_HOSTS:
        return jsonify({"error": "forbidden"}), 403
    return None


def get_genai_client():
    if not GENAI_AVAILABLE:
        raise RuntimeError("google-genai not installed")
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY")
    return genai.Client(api_key=GEMINI_API_KEY)


def transcribe_webm(audio_bytes, language_code="en-US", sample_rate_hertz=48000):
    if not SPEECH_AVAILABLE:
        raise RuntimeError("speech_recognition not installed")
    if not audio_bytes:
        raise RuntimeError("No audio data provided")

    recognizer = sr.Recognizer()

    with tempfile.TemporaryDirectory() as tmpdir:
        webm_path = os.path.join(tmpdir, "input.webm")
        wav_path = os.path.join(tmpdir, "output.wav")

        with open(webm_path, "wb") as handle:
            handle.write(audio_bytes)

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    webm_path,
                    "-ac",
                    "1",
                    "-ar",
                    str(sample_rate_hertz),
                    wav_path
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as exc:
            raise RuntimeError("ffmpeg conversion failed") from exc

        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio, language=language_code)
    except sr.UnknownValueError:
        text = ""
    except sr.RequestError as exc:
        raise RuntimeError("speech recognition request failed") from exc

    return {"text": text, "confidence": None, "alternatives": []}


def speak_text(text):
    if not TTS_AVAILABLE:
        raise RuntimeError("pyttsx3 not installed")
    if not text:
        return {"ok": False, "message": "No text provided"}

    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return {"ok": True}


def build_drive_clients():
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError("Google API client libraries not installed")
    if not os.path.exists(GOOGLE_OAUTH_CLIENT_SECRET):
        raise RuntimeError(
            f"Missing Google OAuth client secret file at: {GOOGLE_OAUTH_CLIENT_SECRET}. "
            f"Download from Google Cloud Console and save as backend/flask/client_secret.json"
        )

    creds = None
    if os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, GOOGLE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_OAUTH_CLIENT_SECRET,
                GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_TOKEN_PATH, "w", encoding="utf-8") as handle:
            handle.write(creds.to_json())

    drive = build("drive", "v3", credentials=creds)
    docs = build("docs", "v1", credentials=creds)
    return drive, docs


def summarize_pdf(file_path, summary_prompt=None):
    if not PDF_AVAILABLE:
        raise RuntimeError("PyPDF2 not installed")
    if not os.path.exists(file_path):
        raise FileNotFoundError("PDF not found")

    reader = PdfReader(file_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        return "No readable text found in PDF."

    client = get_genai_client()
    prompt = summary_prompt or "Summarize this document in concise bullet points."

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[
            f"{prompt}\n\n{text[:15000]}"
        ]
    )
    return response.text


def search_youtube(query, max_results=1):
    """Search YouTube and return video details."""
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError("Google API libraries not installed")
    if not os.path.exists(GOOGLE_OAUTH_CLIENT_SECRET):
        raise FileNotFoundError(f"Missing Google OAuth client secret file at {GOOGLE_OAUTH_CLIENT_SECRET}")
    
    # Authenticate and get credentials
    creds = None
    if os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, GOOGLE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_OAUTH_CLIENT_SECRET,
                GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_TOKEN_PATH, "w", encoding="utf-8") as handle:
            handle.write(creds.to_json())

    youtube = build("youtube", "v3", credentials=creds)
    
    # Search for videos
    search_response = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=max_results,
        type="video"
    ).execute()
    
    videos = []
    for item in search_response.get("items", []):
        video_id = item["id"]["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append({
            "id": video_id,
            "title": item["snippet"]["title"],
            "url": video_url,
            "channel": item["snippet"]["channelTitle"],
            "description": item["snippet"]["description"]
        })
    
    return videos


def create_google_doc(title, content):
    drive, docs = build_drive_clients()
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document"
    }
    doc = drive.files().create(body=file_metadata, fields="id").execute()
    doc_id = doc.get("id")

    docs.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": content
                    }
                }
            ]
        }
    ).execute()
    return doc_id


def check_gmail(max_results=5):
    """Check recent Gmail messages"""
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError("Google API client libraries not installed")
    if not os.path.exists(GOOGLE_OAUTH_CLIENT_SECRET):
        raise RuntimeError(
            f"Missing Google OAuth client secret file at: {GOOGLE_OAUTH_CLIENT_SECRET}. "
            f"Download from Google Cloud Console and save as backend/flask/client_secret.json"
        )

    creds = None
    if os.path.exists(GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, GOOGLE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_OAUTH_CLIENT_SECRET,
                GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_TOKEN_PATH, "w", encoding="utf-8") as handle:
            handle.write(creds.to_json())

    gmail = build("gmail", "v1", credentials=creds)
    
    results = gmail.users().messages().list(
        userId="me",
        maxResults=max_results,
        labelIds=["INBOX"]
    ).execute()
    
    messages = results.get("messages", [])
    if not messages:
        return {"emails": [], "summary": "No recent emails found."}
    
    emails = []
    for msg in messages:
        message = gmail.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
        headers = message.get("payload", {}).get("headers", [])
        
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown")
        
        emails.append({
            "id": msg["id"],
            "subject": subject,
            "from": sender
        })
    
    return {"emails": emails, "count": len(emails)}


def open_app(name):
    command = APP_COMMANDS.get(name)
    if not command:
        raise ValueError("Unsupported app")
    subprocess.Popen(command, shell=False)
    return {"ok": True, "name": name}


def close_app(name):
    process_names = APP_PROCESS_MATCH.get(name)
    if not process_names:
        raise ValueError("Unsupported app")

    closed = []
    for proc in psutil.process_iter(["name", "pid"]):
        if proc.info["name"] in process_names:
            try:
                proc.terminate()
                closed.append(proc.info["pid"])
            except psutil.NoSuchProcess:
                continue

    if not closed:
        return {"ok": False, "message": "App not running"}
    return {"ok": True, "closed": closed}


def set_volume(level):
    if not PYCAW_AVAILABLE:
        raise RuntimeError("pycaw not installed")
    level = max(0, min(int(level), 100))

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    volume.SetMasterVolumeLevelScalar(level / 100.0, None)
    return {"ok": True, "level": level}


def mute_volume(mute=True):
    if not PYCAW_AVAILABLE:
        raise RuntimeError("pycaw not installed")

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    volume.SetMute(1 if mute else 0, None)
    return {"ok": True, "muted": bool(mute)}


def generate_traffic_summary(origin, destination):
    if not origin or not destination:
        raise ValueError("Missing origin or destination")

    client = get_genai_client()

    prompt = (
        "You are Blueee V2 traffic intelligence. "
        "Analyze real-time traffic and generate a concise itinerary. "
        f"Route: {origin} to {destination}. "
        "Return a short traffic description, ETA range, and 3-step itinerary."
    )

    config = None
    if GENAI_AVAILABLE:
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_maps=types.GoogleMapsTool())]
            )
        except Exception:
            config = None

    if config:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=[prompt],
            config=config
        )
    else:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=[prompt]
        )

    return response.text


def _normalize_history(history, limit=20):
    if not isinstance(history, list):
        return []
    normalized = []
    for item in history:
        role = "assistant" if str(item.get("role", "")).lower() == "assistant" else "user"
        text = str(item.get("text", "")).strip()
        if text:
            normalized.append({"role": role, "text": text})
    return normalized[-limit:]


def build_contextual_prompt(text, session_payload):
    history = _normalize_history((session_payload or {}).get("history", []))
    if not history:
        return text

    lines = []
    for item in history:
        label = "Assistant" if item["role"] == "assistant" else "User"
        lines.append(f"{label}: {item['text']}")

    return (
        "You are Blueee V2, a desktop voice assistant. "
        "Use conversation history to answer follow-up questions consistently.\n\n"
        f"Conversation so far:\n{'\n'.join(lines)}\n\n"
        f"Current user message: {text}"
    )


@app.before_request
def restrict_localhost():
    result = ensure_localhost()
    if result:
        return result
    return None


@app.post("/ai")
def ai_router():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    params = payload.get("params", {})
    session_payload = payload.get("session", {})

    try:
        if action == "open_app":
            return jsonify(open_app(params.get("name", "")))
        if action == "close_app":
            return jsonify(close_app(params.get("name", "")))
        if action == "set_volume":
            return jsonify(set_volume(params.get("level", 50)))
        if action == "mute":
            return jsonify(mute_volume(True))
        if action == "unmute":
            return jsonify(mute_volume(False))
        if action == "check_gmail":
            gmail_data = check_gmail(params.get("max_results", 5))
            if not gmail_data.get("emails"):
                return jsonify({"summary": "Your inbox is empty or no new messages."})
            summary_lines = [f"{i+1}. From: {email['from']} - Subject: {email['subject']}" 
                           for i, email in enumerate(gmail_data["emails"])]
            return jsonify({
                "summary": f"You have {gmail_data['count']} recent emails:\n" + "\n".join(summary_lines),
                "emails": gmail_data["emails"]
            })
        if action == "summarize_pdf":
            summary = summarize_pdf(
                params.get("path", ""),
                params.get("prompt")
            )
            return jsonify({"summary": summary})
        if action == "create_doc":
            title = params.get("title") or f"Blueee Research {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"
            doc_id = create_google_doc(title, params.get("content", ""))
            return jsonify({"doc_id": doc_id})
        if action == "search_youtube":
            videos = search_youtube(params.get("query", ""), params.get("max_results", 1))
            if videos:
                return jsonify({
                    "text": f"Found '{videos[0]['title']}' by {videos[0]['channel']}",
                    "response": {
                        "action": "play_video",
                        "url": videos[0]["url"]
                    },
                    "videos": videos
                })
            return jsonify({"text": "No videos found"})
        if action == "speak":
            if not TTS_AVAILABLE:
                return jsonify({"ok": False, "message": "TTS not available"}), 500
            return jsonify(speak_text(params.get("text", "")))

        text = payload.get("text")
        if text:
            text_lower = str(text).lower()
            
            # Auto-detect Gmail intent
            if any(kw in text_lower for kw in ["gmail", "email", "inbox", "check mail", "check email"]):
                try:
                    gmail_data = check_gmail(5)
                    if not gmail_data.get("emails"):
                        return jsonify({"text": "Your inbox is empty or no new messages found."})
                    
                    summary_lines = [
                        f"{i+1}. From: {email['from']} - Subject: {email['subject']}" 
                        for i, email in enumerate(gmail_data["emails"])
                    ]
                    return jsonify({
                        "text": f"You have {gmail_data['count']} recent emails:\n" + "\n".join(summary_lines),
                        "summary": "\n".join(summary_lines)
                    })
                except Exception as e:
                    return jsonify({"text": f"Couldn't check Gmail: {str(e)}. Make sure OAuth is set up."})
            
            # Auto-detect Google Docs creation intent
            if any(kw in text_lower for kw in ["create doc", "make doc", "save to doc", "google doc"]):
                # Extract content from history or current text
                doc_title = f"Blueee Note {datetime.now().strftime('%Y-%m-%d %H-%M')}"
                doc_content = text
                
                # Try to get more context from history
                history = _normalize_history((session_payload or {}).get("history", []))
                if history and len(history) > 1:
                    recent_texts = [h["text"] for h in history[-5:]]
                    doc_content = "\n\n".join(recent_texts)
                
                try:
                    doc_id = create_google_doc(doc_title, doc_content)
                    return jsonify({
                        "text": f"Created Google Doc '{doc_title}' successfully! Document ID: {doc_id}",
                        "doc_id": doc_id
                    })
                except Exception as e:
                    return jsonify({"text": f"Couldn't create document: {str(e)}. Make sure OAuth is set up."})
            
            # Auto-detect YouTube search intent
            if any(kw in text_lower for kw in ["youtube", "play video", "find video", "search video", "show me video", "watch video"]):
                # Extract search query from the text
                search_query = text
                # Remove common trigger words to get cleaner query
                for trigger in ["youtube", "play video", "find video", "search video", "show me video", "watch video", "play", "find", "search", "show me", "watch", "on youtube"]:
                    search_query = search_query.replace(trigger, "")
                search_query = search_query.strip()
                
                if not search_query:
                    return jsonify({"text": "What would you like me to search for on YouTube?"})
                
                try:
                    videos = search_youtube(search_query, max_results=1)
                    if not videos:
                        return jsonify({"text": f"No YouTube videos found for '{search_query}'"})
                    
                    video = videos[0]
                    return jsonify({
                        "text": f"Opening '{video['title']}' by {video['channel']}",
                        "response": {
                            "action": "play_video",
                            "url": video["url"]
                        },
                        "video": video
                    })
                except Exception as e:
                    return jsonify({"text": f"Couldn't search YouTube: {str(e)}. Make sure OAuth is set up."})
            
            # Default: use Gemini with context
            client = get_genai_client()
            prompt = build_contextual_prompt(str(text), session_payload)
            response = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=[prompt]
            )
            return jsonify({"text": response.text})

        return jsonify({"error": "unknown_action"}), 400
    except Exception as exc:
        return jsonify({"error": "ai_error", "message": str(exc)}), 500


@app.post("/traffic")
def traffic_route():
    payload = request.get_json(silent=True) or {}
    origin = payload.get("origin")
    destination = payload.get("destination")

    try:
        summary = generate_traffic_summary(origin, destination)
        return jsonify({"summary": summary})
    except Exception as exc:
        return jsonify({"error": "traffic_error", "message": str(exc)}), 500


@app.post("/transcribe")
def transcribe_route():
    try:
        if "audio" not in request.files:
            return jsonify({"error": "missing_audio"}), 400

        file = request.files["audio"]
        audio_bytes = file.read()
        language = request.form.get("language", "en-US")
        sample_rate = int(request.form.get("sample_rate_hertz", "48000"))

        result = transcribe_webm(audio_bytes, language, sample_rate)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": "transcribe_error", "message": str(exc)}), 500


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="127.0.0.1", port=int(os.getenv("FLASK_PORT", "5000")), debug=debug_mode)
