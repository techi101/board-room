"""Gemini REST wrapper that returns parsed JSON."""
import json
import os

import httpx

MODELS = [m for m in os.environ.get("GEMINI_MODELS", "gemini-3-flash-preview,gemini-3.1-flash-lite,gemini-flash-latest").split(",") if m]


class LLMError(RuntimeError):
    pass


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


async def ask_json(system: str, user: str, temperature: float = 0.7, parts: list | None = None) -> dict:
    """parts: extra Gemini parts, e.g. {"inline_data": {"mime_type": "application/pdf", "data": b64}}."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set")
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": (parts or []) + [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    last = ""
    async with httpx.AsyncClient(timeout=90) as client:
        for model in MODELS:  # fall through on overload / retired model
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            r = await client.post(url, params={"key": key}, json=body)
            if r.status_code == 200:
                break
            last = f"Gemini {model} {r.status_code}: {r.text[:200]}"
            if r.status_code not in (404, 429, 500, 503):
                raise LLMError(last)
        else:
            raise LLMError(last)
    try:
        out_parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in out_parts).strip()
    except (KeyError, IndexError, ValueError) as e:
        raise LLMError(f"Bad Gemini reply: {e}") from e
    return parse_json(text)


def parse_json(text: str) -> dict:
    """Parse the first JSON object, tolerating code fences or trailing text."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    start = text.find("{")
    if start < 0:
        raise LLMError("Bad Gemini reply: no JSON object")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as e:
        raise LLMError(f"Bad Gemini reply: {e}") from e
    if not isinstance(obj, dict):
        raise LLMError("Bad Gemini reply: not an object")
    return obj
