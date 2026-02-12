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

GOOGLE_OAUTH_CLIENT_SECRET = os.getenv(
    "GOOGLE_OAUTH_CLIENT_SECRET",
    os.path.join(os.path.dirname(__file__), "client_secret.json")
)
GOOGLE_TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    os.path.join(os.path.dirname(__file__), "tokens.json")
)

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents"
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
        raise RuntimeError("Missing Google OAuth client secret file")

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
        if action == "speak":
            if not TTS_AVAILABLE:
                return jsonify({"ok": False, "message": "TTS not available"}), 500
            return jsonify(speak_text(params.get("text", "")))

        text = payload.get("text")
        if text:
            client = get_genai_client()
            response = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=[text]
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
