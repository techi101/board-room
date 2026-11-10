"""Board Room API. Run: uvicorn backend.app:app --reload  (from the repo root)."""
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent


def _load_env(path=ROOT / ".env"):
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

from . import board, context, gnani, limits, llm  # noqa: E402
from .tracks import TRACKS, public  # noqa: E402

app = FastAPI(title="Board Room")
FRONTEND = ROOT / "frontend"
MAX_TTS_CHARS = 400
MAX_AUDIO_BYTES = 4 * 1024 * 1024
MAX_PDF_BYTES = 3 * 1024 * 1024
TAG_RE = re.compile(r"<[^>]+>")
LANG_RE = "^(en|hi)$"


def ip_of(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (req.client.host if req.client else "?")


def guard(req: Request, kind: str):
    if not limits.allow(ip_of(req), kind):
        raise HTTPException(429, f"daily limit reached for {kind}")


class Turn(BaseModel):
    speaker: str
    question: str
    answer: str = ""
    seconds: float = 0


class Session(BaseModel):
    track: str = "upsc"
    lang: str = Field("en", pattern=LANG_RE)
    plan: str = Field("short", pattern="^(short|full)$")
    pressure: str = Field("standard", pattern="^(friendly|standard|stress)$")
    dossier: dict = {}
    history: list[Turn] = []


class TTSRequest(BaseModel):
    text: str
    voice: str
    lang: str = Field("en", pattern=LANG_RE)


class CloneSpeakRequest(BaseModel):
    text: str
    embedding: dict | list
    lang: str = Field("en", pattern=LANG_RE)


def _check_track(track: str):
    if track not in TRACKS:
        raise HTTPException(400, "unknown track")


@app.get("/api/status")
def status():
    return {"gnani": gnani.api_key() is not None, "llm": llm.available(), "usage": limits.usage(),
            "pressure": {k: v["limit"] for k, v in board.PRESSURE.items()}, "tracks": public()}


@app.post("/api/intake")
async def intake(request: Request, track: str = Form(...), fields: str = Form("{}"), resume_text: str = Form(""),
                 github_url: str = Form(""), jd: str = Form(""), resume: UploadFile | None = File(None)):
    _check_track(track)
    guard(request, "intake")
    try:
        f = json.loads(fields)
        assert isinstance(f, dict)
    except (ValueError, AssertionError):
        raise HTTPException(400, "bad fields")
    pdf = None
    if resume is not None and resume.filename:
        pdf = await resume.read()
        if len(pdf) > MAX_PDF_BYTES or not pdf.startswith(b"%PDF"):
            raise HTTPException(400, "resume must be a PDF under 3 MB")
    try:
        return await context.build_dossier(track, {k: str(v)[:300] for k, v in f.items()}, pdf,
                                           resume_text[:10000], github_url.strip(), jd[:5000])
    except llm.LLMError as e:
        raise HTTPException(502, str(e))


@app.post("/api/turn")
async def turn(req: Session, request: Request):
    _check_track(req.track)
    guard(request, "turn")
    history = [t.model_dump() for t in req.history]
    react = None
    if history:
        last = history[-1]
        react = board.reaction(req.track, req.lang, req.pressure, last["answer"], last["seconds"], len(history))
    try:
        nxt = await board.next_turn(req.track, req.lang, req.plan, req.pressure, req.dossier, history)
    except (llm.LLMError, KeyError, StopIteration) as e:
        raise HTTPException(502, f"panel error: {e}")
    return {"reaction": react, "next": nxt}


@app.post("/api/report")
async def report(req: Session):
    _check_track(req.track)
    try:
        return await board.report(req.track, req.lang, req.dossier, [t.model_dump() for t in req.history])
    except llm.LLMError as e:
        raise HTTPException(502, str(e))


@app.post("/api/tts")
async def tts(req: TTSRequest, request: Request):
    if len(req.text) > MAX_TTS_CHARS:
        raise HTTPException(400, "text too long")
    if gnani.api_key() is None:
        raise HTTPException(503, "no-gnani-key")
    lang = board.LANG[req.lang]["tts"]
    text = board.spoken(req.text, req.lang)
    if not gnani.cached(text, req.voice, lang):  # cached audio is free
        guard(request, "tts")
        if not limits.spend_tts(len(TAG_RE.sub("", text))):
            raise HTTPException(429, "daily voice budget used up")
    try:
        audio = await gnani.speak(text, req.voice, lang)
    except gnani.GnaniError as e:
        raise HTTPException(e.status, str(e))
    return Response(audio, media_type="audio/mpeg")


@app.post("/api/stt")
async def stt(request: Request, audio: UploadFile = File(...), lang: str = Form("en"), seconds: float = Form(30)):
    if lang not in board.LANG:
        raise HTTPException(400, "bad lang")
    if gnani.api_key() is None:
        raise HTTPException(503, "no-gnani-key")
    guard(request, "stt")
    if not limits.spend_stt(min(max(seconds, 1), 60)):
        raise HTTPException(429, "daily listening budget used up")
    data = await audio.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(400, "audio too large")
    try:
        return {"transcript": await gnani.transcribe(data, board.LANG[lang]["stt"])}
    except gnani.GnaniError as e:
        raise HTTPException(e.status, str(e))


@app.post("/api/clone/embed")
async def clone_embed(request: Request, audio: UploadFile = File(...)):
    if gnani.api_key() is None:
        raise HTTPException(503, "no-gnani-key")
    guard(request, "clone")
    data = await audio.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(400, "audio too large")
    try:
        return {"embedding": await gnani.clone_embedding(data)}
    except gnani.GnaniError as e:
        raise HTTPException(e.status, str(e))


@app.post("/api/clone/speak")
async def clone_speak(req: CloneSpeakRequest, request: Request):
    text = TAG_RE.sub("", req.text).strip()
    if not text or len(text) > MAX_TTS_CHARS:
        raise HTTPException(400, "bad text")
    if gnani.api_key() is None:
        raise HTTPException(503, "no-gnani-key")
    guard(request, "clone_speak")
    if not limits.spend_tts(len(text)):
        raise HTTPException(429, "daily voice budget used up")
    try:
        audio = await gnani.speak_cloned(text, req.embedding, board.LANG[req.lang]["tts"])
    except gnani.GnaniError as e:
        raise HTTPException(e.status, str(e))
    return Response(audio, media_type="audio/mpeg")


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
