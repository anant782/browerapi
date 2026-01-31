import os
import uuid
import time
import edge_tts
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from urllib.parse import unquote

# ===============================
# CONFIG
# ===============================

APP_NAME = "Private Edge TTS API"
MAX_TEXT_LENGTH = 350
RATE_LIMIT_SECONDS = 2
AUDIO_FOLDER = "audio_files"

DEFAULT_VOICE = "hi-IN-SwaraNeural"

ALLOWED_VOICES = [
    "hi-IN-SwaraNeural",
    "hi-IN-MadhurNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural"
]

# ===============================
# APP INIT
# ===============================

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# STORAGE
# ===============================

if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

ip_last_request: Dict[str, float] = {}

# ===============================
# HELPERS
# ===============================

def clean_old_files(max_age=120):
    now = time.time()
    for f in os.listdir(AUDIO_FOLDER):
        path = os.path.join(AUDIO_FOLDER, f)
        if os.path.isfile(path):
            if now - os.path.getmtime(path) > max_age:
                try:
                    os.remove(path)
                except:
                    pass

def is_rate_limited(ip: str):
    now = time.time()
    last = ip_last_request.get(ip, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return True
    ip_last_request[ip] = now
    return False

def sanitize_rate_pitch(value: str):
    if not value:
        return value
    return value.replace(" ", "")

# ===============================
# ROUTES
# ===============================

@app.get("/")
def home():
    return {
        "status": "running",
        "voices": ALLOWED_VOICES
    }

@app.get("/tts")
async def tts(
    request: Request,
    text: str = Query(...),
    voice: str = Query(DEFAULT_VOICE),
    rate: str = Query("0%"),
    pitch: str = Query("0Hz")
):
    client_ip = request.client.host

    if is_rate_limited(client_ip):
        return JSONResponse(
            {"error": "Too many requests"},
            status_code=429
        )

    # Decode URL encoded text
    text = unquote(text).strip()

    if not text:
        return JSONResponse(
            {"error": "Empty text"},
            status_code=400
        )

    if len(text) > MAX_TEXT_LENGTH:
        return JSONResponse(
            {"error": "Text too long"},
            status_code=400
        )

    if voice not in ALLOWED_VOICES:
        return JSONResponse(
            {"error": "Voice not allowed"},
            status_code=400
        )

    # FIX: sanitize rate & pitch
    rate = sanitize_rate_pitch(rate)
    pitch = sanitize_rate_pitch(pitch)

    # Validate rate
    if not rate.endswith("%"):
        return JSONResponse(
            {"error": "Invalid rate format. Use +10% or -10%"},
            status_code=400
        )

    # Validate pitch
    if not pitch.endswith("Hz"):
        return JSONResponse(
            {"error": "Invalid pitch format. Use +2Hz or -2Hz"},
            status_code=400
        )

    clean_old_files()

    file_name = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(AUDIO_FOLDER, file_name)

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch
        )
        await communicate.save(file_path)
    except Exception as e:
        return JSONResponse(
            {"error": "TTS failed", "detail": str(e)},
            status_code=500
        )

    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename="speech.mp3"
    )

@app.get("/health")
def health():
    return {"ok": True}
