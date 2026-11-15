import json

import pytest
from fastapi.testclient import TestClient

from backend import board, context, limits
from backend.app import app
from backend.tracks import QTYPES, TRACKS

c = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_limits():
    limits.reset()


def test_status_lists_all_tracks():
    j = c.get("/api/status").json()
    assert {"upsc", "software", "ca", "mba", "bank", "core", "consulting", "custom"} <= set(j["tracks"])


@pytest.mark.parametrize("track", list(TRACKS))
def test_track_config_is_consistent(track):
    t = TRACKS[track]
    ids = {m["id"] for m in t["panel"]}
    assert 2 <= len(ids) <= 5
    for plan in t["plans"].values():
        assert plan[-1][1] == "closing"
        for mid, q in plan:
            assert mid in ids and q in QTYPES
    assert len(t["rubric"]) == 5


def test_reaction_rules():
    assert board.reaction("upsc", "en", "standard", "word " * 30, 90, 1)["kind"] == "interrupt"
    assert board.reaction("upsc", "en", "stress", "word " * 30, 61, 1)["kind"] == "interrupt"
    assert board.reaction("upsc", "en", "friendly", "word " * 30, 100, 1) is None
    assert board.reaction("ca", "hi", "standard", "पता नहीं", 3, 1)["kind"] == "short"
    assert board.reaction("software", "en", "standard", "a fairly complete answer with many words in it", 20, 2)["kind"] == "whisper"


def test_delivery_metrics_count_fillers():
    h = [{"answer": "um I basically think um that like it works", "seconds": 6}]
    d = board.delivery("en", h)
    assert d["filler_words"]["um"] == 2 and d["filler_total"] == 4 and d["words_per_minute"] == 90


@pytest.mark.parametrize("track", ["upsc", "software", "consulting"])
def test_offline_turns_run_to_closing(monkeypatch, track):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    s = {"track": track, "lang": "en", "plan": "short", "dossier": {}, "history": []}
    n = None
    for _ in range(len(TRACKS[track]["plans"]["short"])):
        n = c.post("/api/turn", json=s).json()["next"]
        assert not n["done"]
        s["history"].append({"speaker": n["speaker"], "question": n["text"], "answer": "My answer is long enough here", "seconds": 10})
    assert n["closing"]
    assert c.post("/api/turn", json=s).json()["next"]["done"]


def test_unknown_track_and_bad_lang_rejected():
    assert c.post("/api/turn", json={"track": "astronaut"}).status_code == 400
    assert c.post("/api/turn", json={"track": "upsc", "lang": "fr"}).status_code == 422


def test_tts_without_key_signals_fallback(monkeypatch):
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    assert c.post("/api/tts", json={"text": "hello", "voice": "Avinash", "lang": "en"}).status_code == 503


def test_tts_budget_blocks(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "x")
    monkeypatch.setattr(limits, "DAILY_TTS_CHARS", 3)
    r = c.post("/api/tts", json={"text": "hello there, not cached", "voice": "Avinash", "lang": "en"})
    assert r.status_code == 429


def test_intake_rejects_non_pdf():
    r = c.post("/api/intake", data={"track": "software", "fields": "{}"}, files={"resume": ("r.pdf", b"hello", "application/pdf")})
    assert r.status_code == 400


def test_intake_without_material_returns_fields(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = c.post("/api/intake", data={"track": "upsc", "fields": json.dumps({"home": "Bihar", "hobbies": ""})})
    assert r.status_code == 200 and r.json()["fields"] == {"home": "Bihar"}


def test_parse_github_and_file_picking():
    assert context.parse_github("https://github.com/techi101/launchswitch.git") == ("techi101", "launchswitch")
    assert context.parse_github("github.com/techi101") == ("techi101", None)
    with pytest.raises(context.ContextError):
        context.parse_github("https://gitlab.com/x/y")
    tree = [{"type": "blob", "path": p, "size": 4000} for p in
            ["README.md", "package.json", "src/app.py", "node_modules/x/index.js", "tests/test_app.py", "dist/bundle.min.js", "src/utils/helpers.py"]]
    readme, manifest, code = context.pick_files(tree)
    assert readme == "README.md" and manifest == "package.json"
    assert code[0] == "src/app.py" and "node_modules/x/index.js" not in code and "tests/test_app.py" not in code


def test_per_ip_limit():
    for _ in range(limits.PER_IP["intake"]):
        assert limits.allow("1.2.3.4", "intake")
    assert not limits.allow("1.2.3.4", "intake")


def test_looks_like_question():
    assert board.looks_like_question("Sorry, which file do you mean?", "en")
    assert board.looks_like_question("can you repeat the question", "en")
    assert board.looks_like_question("क्या आप प्रश्न दोहरा सकते हैं", "hi")
    assert not board.looks_like_question("I used FastAPI because it is async and simple to test", "en")
    assert not board.looks_like_question("", "en")
    long_answer = "I built the backend in FastAPI and wrote the retry logic myself and later in my project I added caching"
    assert not board.looks_like_question(long_answer, "en")


def test_candidate_question_gets_reply_without_using_a_slot(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    s = {"track": "software", "lang": "en", "plan": "short", "dossier": {}, "history": []}
    first = c.post("/api/turn", json=s).json()["next"]
    s["history"].append({"speaker": first["speaker"], "question": first["text"], "qtype": first["qtype"],
                         "answer": "Sorry, can you repeat that?", "seconds": 2})
    j = c.post("/api/turn", json=s).json()
    r = j["next"]
    assert j["reaction"] is None  # no sigh at a short clarifying question
    assert r["kind"] == "reply" and r["speaker"] == first["speaker"] and r["index"] == first["index"]
    assert first["text"] in r["text"]
    s["history"].append({"speaker": r["speaker"], "question": r["text"], "kind": "reply",
                         "answer": "My answer is long enough here", "seconds": 10})
    n2 = c.post("/api/turn", json=s).json()["next"]
    assert n2["kind"] == "question" and n2["index"] == 1


def test_reply_loop_is_capped(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    q = {"speaker": "hr", "question": "Tell me about yourself.", "answer": "Can you repeat?", "seconds": 2}
    h = [q, q | {"kind": "reply"}, q | {"kind": "reply"}]
    s = {"track": "software", "lang": "en", "plan": "short", "dossier": {}, "history": h}
    assert c.post("/api/turn", json=s).json()["next"]["kind"] == "question"
