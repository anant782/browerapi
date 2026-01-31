import os
import uuid
import asyncio
import tempfile
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse
import edge_tts

app = FastAPI()

# -------------------------
# Helper: sanitize params
# -------------------------
def clean_param(value: str):
    return value.replace(" ", "").strip()

# -------------------------
# TTS Endpoint
# -------------------------
@app.get("/tts")
async def tts(
    text: str = Query(..., min_length=1),
    voice: str = "hi-IN-MadhurNeural",
    rate: str = "+6%",
    pitch: str = "0Hz",
):
    try:
        # Clean inputs
        rate = clean_param(rate)
        pitch = clean_param(pitch)

        # Validation (important)
        if not rate.startswith(("+", "-")) or not rate.endswith("%"):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid rate format. Use +6% or -6%"}
            )

        if not pitch.endswith("Hz"):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid pitch format. Use +1Hz or -1Hz"}
            )

        # Generate unique filename
        unique_id = uuid.uuid4().hex
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"tts_{unique_id}.mp3")

        # Edge TTS
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

        await communicate.save(audio_path)

        # Stream audio (NO CACHE)
        def audio_stream():
            with open(audio_path, "rb") as f:
                yield from f
            # cleanup
            os.remove(audio_path)

        return StreamingResponse(
            audio_stream(),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "TTS failed", "detail": str(e)},
        )

# -------------------------
# Root check
# -------------------------
@app.get("/")
def root():
    return {"status": "Edge TTS API running"}
