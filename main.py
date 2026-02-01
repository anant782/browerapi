# filename: edge_tts_api.py

import os
import uuid
import time
import edge_tts
from fastapi import FastAPI, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from urllib.parse import unquote

# ===============================
# CONFIG
# ===============================
MAX_TEXT_LENGTH = 350
RATE_LIMIT_SECONDS = 2
AUDIO_FOLDER = "audio_files"

DEFAULT_VOICE = "hi-IN-MadhurNeural"
ALLOWED_VOICES = [
    "hi-IN-SwaraNeural",
    "hi-IN-MadhurNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-IN-ArjunNeural",
    "en-US-AndrewNeural"
]

# ===============================
# APP INIT
# ===============================
app = FastAPI(title="Private Edge TTS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# STORAGE
# ===============================
os.makedirs(AUDIO_FOLDER, exist_ok=True)
ip_last_request: Dict[str, float] = {}

# ===============================
# HELPERS
# ===============================
def rate_limited(ip: str):
    now = time.time()
    last = ip_last_request.get(ip, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return True
    ip_last_request[ip] = now
    return False


def clean_old_files(max_age=120):
    now = time.time()
    for f in os.listdir(AUDIO_FOLDER):
        path = os.path.join(AUDIO_FOLDER, f)
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age:
            try:
                os.remove(path)
            except:
                pass


def normalize_rate(value: str):
    value = value.replace(" ", "")
    if value.endswith("%") and not value.startswith(("+", "-")):
        value = "+" + value
    return value


def normalize_pitch(value: str):
    value = value.replace(" ", "")
    if value.endswith("Hz") and not value.startswith(("+", "-")):
        value = "+" + value
    return value


def sanitize_text(text: str) -> str:
    """
    Fixes Edge TTS last-word mute issue
    """
    text = unquote(text).strip()

    # remove line breaks (important for Hindi)
    text = text.replace("\n", " ")

    # force sentence ending
    if not text.endswith((".", "।", "!", "?")):
        text += "।"

    # small silent pause trigger
    text += " "

    return text


# ===============================
# ROUTES
# ===============================
@app.get("/")
def home():
    return {"status": "running", "voices": ALLOWED_VOICES}


@app.get("/tts")
async def tts(
    request: Request,
    text: str = Query(...),
    voice: str = Query(DEFAULT_VOICE),
    rate: str = Query("0%"),
    pitch: str = Query("0Hz")
):
    ip = request.client.host

    if rate_limited(ip):
        return JSONResponse({"error": "Too many requests"}, status_code=429)

    if not text.strip():
        return JSONResponse({"error": "Empty text"}, status_code=400)

    if len(text) > MAX_TEXT_LENGTH:
        return JSONResponse({"error": "Text too long"}, status_code=400)

    if voice not in ALLOWED_VOICES:
        return JSONResponse({"error": "Voice not allowed"}, status_code=400)

    rate = normalize_rate(rate)
    pitch = normalize_pitch(pitch)

    if not rate.endswith("%"):
        return JSONResponse({"error": "Invalid rate format"}, status_code=400)

    if not pitch.endswith("Hz"):
        return JSONResponse({"error": "Invalid pitch format"}, status_code=400)

    clean_old_files()

    # 🔥 text fix applied here
    text = sanitize_text(text)

    file_path = os.path.join(AUDIO_FOLDER, f"{uuid.uuid4().hex}.mp3")

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

    def stream_audio(path):
        with open(path, "rb") as f:
            yield from f

    return StreamingResponse(
        stream_audio(file_path),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-store",
            "Pragma": "no-cache"
        },
    )
