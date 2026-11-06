"""Thin client for Gnani speech APIs (Prisma STT, Timbre TTS, voice clone).

Docs: https://docs.gnani.ai. All calls are REST so the app also runs on serverless hosts.
Every call goes through one semaphore with retry, because builders report a low
concurrent-request limit per key (429 on a second simultaneous request).
"""
import asyncio
import hashlib
import os
import tempfile
from pathlib import Path

import httpx

from .limits import gnani_lock

BASE = "https://api.vachana.ai"
_default_cache = Path(tempfile.gettempdir()) / "board_room_tts" if os.environ.get("VERCEL") else Path(__file__).parent / "tts_cache"
CACHE_DIR = Path(os.environ.get("TTS_CACHE_DIR", _default_cache))


def api_key() -> str | None:
    return os.environ.get("GNANI_API_KEY") or None


class GnaniError(RuntimeError):
    def __init__(self, msg: str, status: int = 502):
        super().__init__(msg)
        self.status = status


def _headers() -> dict:
    key = api_key()
    if not key:
        raise GnaniError("GNANI_API_KEY is not set", 503)
    return {"X-API-Key-ID": key}


async def _post(path: str, label: str, timeout: float = 60, **kw) -> httpx.Response:
    last = None
    async with gnani_lock:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(3):
                r = await client.post(f"{BASE}{path}", headers=_headers(), **kw)
                if r.status_code == 200:
                    return r
                last = r
                if r.status_code not in (429, 500, 502, 503):
                    break
                await asyncio.sleep(1.2 * (attempt + 1))
    raise GnaniError(f"{label} {last.status_code}: {last.text[:300]}", 429 if last.status_code == 429 else 502)


async def transcribe(wav_bytes: bytes, language: str) -> str:
    """Prisma v2.5 REST STT. Audio must be WAV/MP3/etc with a matching filename, <= 60 s."""
    r = await _post("/stt/v3", "STT", data={"language_code": language, "format": "transcribe"},
                    files={"audio_file": ("answer.wav", wav_bytes, "audio/wav")})
    return r.json().get("transcript", "")


def _cache_path(payload: str) -> Path:
    return CACHE_DIR / (hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24] + ".bin")


def cached(text: str, voice: str, language: str, speed: float = 1.0, container: str = "mp3") -> bool:
    return _cache_path(f"v3|{voice}|{language}|{speed}|{container}|{text}").exists()


async def speak(text: str, voice: str, language: str = "auto", speed: float = 1.0, container: str = "mp3") -> bytes:
    """Timbre v3.0 REST TTS. Cached on disk so repeats cost no credits."""
    path = _cache_path(f"v3|{voice}|{language}|{speed}|{container}|{text}")
    if path.exists():
        return path.read_bytes()
    body = {
        "text": text, "voice": voice, "model": "timbre-v3.0", "language": language, "speed": speed,
        "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2, "container": container},
    }
    r = await _post("/api/v1/tts/inference", "TTS", json=body)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    except OSError:
        pass
    return r.content


async def clone_embedding(audio_bytes: bytes, filename: str = "voice.wav") -> dict:
    """Voice-clone embedding from 5-30 s of the user's own voice. Returns {embedding, shape, dtype}."""
    r = await _post("/api/v1/tts/voice-clone/embeddings", "Clone",
                    files={"audio_file": (filename, audio_bytes, "audio/wav")})
    j = r.json()
    emb = (j.get("data") or {}).get("voice_clone_embedding") or j.get("voice_clone_embedding")
    if emb is None:
        raise GnaniError(f"Clone: no embedding in response keys {list(j)}")
    return emb


async def speak_cloned(text: str, embedding, language: str = "auto", container: str = "mp3") -> bytes:
    """One sentence in the cloned voice (the clone model cannot stream or take tags)."""
    spk = embedding if isinstance(embedding, dict) and "embedding" in embedding \
        else {"embedding": embedding, "shape": [1, 768], "dtype": "torch.bfloat16"}
    body = {
        "text": text, "model": "vachana-vc-v1", "language": language, "speaker_embedding": spk,
        "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2, "container": container},
    }
    r = await _post("/api/v1/tts/inference", "Cloned TTS", timeout=90, json=body)
    return r.content
