"""Vercel entry point: exposes the FastAPI app."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app import app  # noqa: E402,F401


# Safety net: if a platform rewrite hands us "/api/index", restore the original path.
_inner = app


async def app(scope, receive, send):  # noqa: F811
    if scope.get("type") in ("http", "websocket") and scope.get("path", "").startswith("/api/index"):
        hdrs = dict(scope.get("headers") or [])
        orig = (hdrs.get(b"x-matched-path") or hdrs.get(b"x-original-path") or b"").decode()
        if orig and not orig.startswith("/api/index"):
            scope = dict(scope, path=orig, raw_path=orig.encode())
    await _inner(scope, receive, send)
