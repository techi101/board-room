"""Protect the free Gnani credits: per-visitor daily caps + a global daily TTS character budget.

In-memory (resets on restart / per serverless instance). Good enough for a demo; when a cap is
hit the browser falls back to its own voice and typing, so the app never just breaks.
"""
import asyncio
import datetime as dt
import os
from collections import defaultdict

PER_IP = {"intake": 6, "tts": 120, "stt": 80, "clone": 3, "clone_speak": 30, "turn": 80}
DAILY_TTS_CHARS = int(os.environ.get("GNANI_DAILY_TTS_CHARS", "60000"))
DAILY_STT_SECONDS = int(os.environ.get("GNANI_DAILY_STT_SECONDS", "7200"))

_counts: dict = defaultdict(int)
_global: dict = defaultdict(int)
gnani_lock = asyncio.Semaphore(int(os.environ.get("GNANI_CONCURRENCY", "2")))


def _day() -> str:
    return dt.date.today().isoformat()


def allow(ip: str, kind: str) -> bool:
    key = (_day(), ip, kind)
    if _counts[key] >= PER_IP[kind]:
        return False
    _counts[key] += 1
    return True


def spend_tts(chars: int) -> bool:
    key = (_day(), "tts_chars")
    if _global[key] + chars > DAILY_TTS_CHARS:
        return False
    _global[key] += chars
    return True


def spend_stt(seconds: float) -> bool:
    key = (_day(), "stt_seconds")
    if _global[key] + seconds > DAILY_STT_SECONDS:
        return False
    _global[key] += seconds
    return True


def usage() -> dict:
    d = _day()
    return {"tts_chars": _global[(d, "tts_chars")], "tts_chars_budget": DAILY_TTS_CHARS,
            "stt_seconds": round(_global[(d, "stt_seconds")]), "stt_seconds_budget": DAILY_STT_SECONDS}


def reset():
    _counts.clear()
    _global.clear()
