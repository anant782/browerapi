import os
import uuid
import time
import asyncio
import edge_tts
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

# ===============================
# BASIC CONFIG
# ===============================

APP_NAME = "Free Edge TTS API"
MAX_TEXT_LENGTH = 350        # safe limit
RATE_LIMIT_SECONDS = 3       # per IP
AUDIO_FOLDER = "audio_files"

DEFAULT_VOICE = "hi-IN-MadhurNeural"

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
# STORAGE + RATE LIMIT
# ===============================

if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

ip_last_request: Dict[str, float] = {}

# ===============================
# UTILS
# ===============================

def clean_old_files(max_age=120):
    now = time.time()
    for file in os.listdir(AUDIO_FOLDER):
        path = os.path.join(AUDIO_FOLDER, file)
        if os.path.isfile(path):
            if now - os.path.getmtime(path) > max_age:
                try:
                    os.remove(path)
                except:
                    pass

def rate_limited(ip: str):
    now = time.time()
    last = ip_last_request.get(ip, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return True
    ip_last_request[ip] = now
    return False

# ===============================
# ROUTES
# ===============================

@app.get("/")
def home():
    return {
        "status": "running",
        "engine": "Microsoft Edge TTS",
        "voices": ALLOWED_VOICES
    }

@app.get("/voices")
def voices():
    return {"voices": ALLOWED_VOICES}

@app.get("/tts")
async def tts(
    request: Request,
    text: str = Query(..., min_length=1),
    voice: str = Query(DEFAULT_VOICE),
    rate: str = "+0%",
    pitch: str = "+0Hz"
):
    client_ip = request.client.host

    # Rate limit
    if rate_limited(client_ip):
        return JSONResponse(
            {"error": "Too many requests"},
            status_code=429
        )

    # Text limit
    if len(text) > MAX_TEXT_LENGTH:
        return JSONResponse(
            {"error": "Text too long"},
            status_code=400
        )

    # Voice check
    if voice not in ALLOWED_VOICES:
        return JSONResponse(
            {"error": "Voice not allowed"},
            status_code=400
        )

    # Cleanup
    clean_old_files()

    file_id = str(uuid.uuid4())
    file_path = f"{AUDIO_FOLDER}/{file_id}.mp3"

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
rate = rate.replace(" ", "")
pitch = pitch.replace(" ", "")

# ===============================
# HEALTH CHECK
# ===============================

@app.get("/health")
def health():
    return {"ok": True}
