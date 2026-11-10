"""Interview engine: next question, rule-based reactions, delivery metrics, feedback report.

Rule-based parts (interruptions, sighs, whispers, delivery metrics) are deterministic and
labelled as such in the UI. Question wording and feedback come from the LLM, grounded in the dossier.
"""
import json
import re

from . import llm
from .tracks import QTYPES, TRACKS, member

LANG = {
    "hi": {"name": "Hindi (Devanagari script; keep common English technical terms in English)", "stt": "hi-IN", "tts": "hi-IN"},
    "en": {"name": "Indian English", "stt": "en-IN", "tts": "en-IN"},
}

PRESSURE = {
    "friendly": {"limit": 120, "style": "Warm and encouraging; give a small hint if the candidate is stuck."},
    "standard": {"limit": 90, "style": "Polite but probing, like a real panel."},
    "stress": {"limit": 60, "style": "A stress interview: skeptical, challenge weak claims directly, interrupt vague talk. Never rude or personal."},
}
SHORT_ANSWER_WORDS = 6

INTERRUPT = {
    "hi": "<clears throat> धन्यवाद, इतना पर्याप्त है। आगे बढ़ते हैं।",
    "en": "<clears throat> Thank you, that is enough on this. Let us move on.",
}
SHORT_REACTION = {"hi": "<sigh> ठीक है।", "en": "<sigh> All right."}
WHISPERS = {
    "hi": ["<whispers> दिलचस्प उत्तर है।", "<whispers> इस पर फिर लौटेंगे।", "<whispers> ठीक है, नोट कर लीजिए।"],
    "en": ["<whispers> Interesting answer.", "<whispers> Let us come back to this.", "<whispers> Note that down."],
}

FILLERS = {
    "en": ["um", "uh", "basically", "actually", "like", "you know", "kind of", "sort of", "i mean"],
    "hi": ["मतलब", "यानी", "बेसिकली", "एक्चुअली", "तो", "जैसे", "अं", "हम्म", "um", "basically", "actually", "like"],
}


def reaction(track: str, lang: str, pressure: str, answer: str, seconds: float, turn: int) -> dict | None:
    """Deterministic panel reaction to the last answer. None means no reaction."""
    panel = TRACKS[track]["panel"]
    lead, side = panel[0]["id"], panel[1]["id"] if len(panel) > 1 else panel[0]["id"]
    if seconds >= PRESSURE[pressure]["limit"]:
        return {"speaker": lead, "text": INTERRUPT[lang], "kind": "interrupt"}
    if len(answer.split()) < SHORT_ANSWER_WORDS:
        return {"speaker": lead, "text": SHORT_REACTION[lang], "kind": "short"}
    if turn % 3 == 2:
        lines = WHISPERS[lang]
        return {"speaker": side, "text": lines[(turn // 3) % len(lines)], "kind": "whisper"}
    return None


def delivery(lang: str, history: list[dict]) -> dict:
    """Rule-based speaking metrics. Approximate: speech recognition may drop some fillers."""
    answered = [h for h in history if h.get("answer")]
    words = sum(len(h["answer"].split()) for h in answered)
    secs = sum(h.get("seconds", 0) for h in answered)
    counts = {}
    for h in answered:
        text = " " + re.sub(r"[^\w\s]", " ", h["answer"].lower()) + " "
        for f in FILLERS[lang]:
            n = text.count(f" {f} ")
            if n:
                counts[f] = counts.get(f, 0) + n
    return {
        "answers": len(answered),
        "words_per_minute": round(words / secs * 60) if secs > 5 else None,
        "avg_answer_seconds": round(secs / len(answered)) if answered else 0,
        "longest_answer_seconds": round(max((h.get("seconds", 0) for h in answered), default=0)),
        "filler_words": dict(sorted(counts.items(), key=lambda x: -x[1])[:5]),
        "filler_total": sum(counts.values()),
    }


# Raw paths like "api/index.js" or "/tmp" are read out as "slash ..." by TTS. Rewrite them as words before speaking.
_TOKEN_RE = re.compile(r"(?<![\w/.\-])/?[\w.\-]+(?:/[\w.\-]*)*")
_EXT_RE = re.compile(r"\.(py|js|jsx|ts|tsx|json|md|txt|html|css|java|cpp|c|h|go|rs|rb|php|yml|yaml|toml|sql|sh|ipynb|kt|swift|dart|vue|env)$", re.I)
_URL_RE = re.compile(r"https?://\S+")


def _say_file(name: str) -> str:
    return _EXT_RE.sub(lambda m: " dot " + m.group(1), name).replace("_", " ")


def _is_path(tok: str) -> bool:
    if not re.search(r"[A-Za-z]", tok):
        return False  # 5/10, 50/50
    if "/" in tok:  # api/index.js, /tmp, src/utils/ (but not and/or)
        return tok.startswith("/") or tok.endswith("/") or bool(_EXT_RE.search(tok)) or tok.count("/") >= 2
    return bool(_EXT_RE.search(tok))


def spoken(text: str, lang: str = "en") -> str:
    """Text to send to TTS: file paths become words. The on-screen caption keeps the original."""
    text = _URL_RE.sub("the link" if lang == "en" else "लिंक", text)

    def fix(m):
        tok = m.group(0).rstrip(".")
        tail = m.group(0)[len(tok):]
        if not _is_path(tok):
            return m.group(0)
        parts = [x for x in tok.strip("/").split("/") if x]
        if not parts:
            return m.group(0)
        if len(parts) == 1:
            if "/" in tok and not _EXT_RE.search(tok):  # /tmp, utils/
                return (f"{parts[0]} फ़ोल्डर" if lang == "hi" else f"the {parts[0]} folder") + tail
            return _say_file(parts[0]) + tail
        f, folder = _say_file(parts[-1]), parts[-2].replace("_", " ")
        if lang == "hi":
            return f"{folder} फ़ोल्डर की {f} फ़ाइल" + tail
        return f"{f} in the {folder} folder" + tail
    return _TOKEN_RE.sub(fix, text)


SYSTEM_TURN = """You are one member of a realistic interview panel in India. {format}
You write ONLY what this one panel member says next. Rules:
- Speak only in {lang_name}. Under 50 words. One question at a time. Sound like a human interviewer, not a quiz.
- Tone: {style}
- Personal questions may use ONLY facts in the candidate dossier. Never invent their projects, files, jobs or numbers.
- You are speaking out loud. Name a file the way a person says it ("the index file in your api folder"), never as a raw path with slashes.
- If the previous answer was vague, one-sided or shaky AND it was this member's area, you may ask a pointed follow-up instead of the planned question type.
- Do not repeat a question already asked. Never mention being an AI. Never say "UPSC" or "Commission".
- You may begin with at most one tag from: <pauses>, <clears throat>, <slow>. No other tags.
Return JSON: {{"text": "...", "is_followup": true|false}}"""


def _history_text(track: str, history: list[dict]) -> str:
    lines = []
    for h in history:
        lines.append(f"{member(track, h['speaker'])['title']}: {h['question']}")
        lines.append(f"Candidate: {h.get('answer') or '(no answer)'}")
    return "\n".join(lines) or "(interview not started)"


def _brief(dossier: dict) -> str:
    d = {k: v for k, v in dossier.items() if v and k not in ("repo",)}
    return json.dumps(d, ensure_ascii=False)[:6000]


async def next_turn(track: str, lang: str, plan: str, pressure: str, dossier: dict, history: list[dict]) -> dict:
    t = TRACKS[track]
    order = t["plans"][plan]
    idx = len(history)
    if idx >= len(order):
        return {"done": True}
    mid, qtype = order[idx]
    m = member(track, mid)
    is_last = qtype == "closing"
    user = (
        f"Candidate dossier: {_brief(dossier)}\n\nTrack fundamentals: {t['fundamentals']}\n\n"
        f"Interview so far:\n{_history_text(track, history)}\n\n"
        f"Now speaking: {m['title']} (focus: {m['focus']}).\nPlanned question type: {qtype}: {QTYPES[qtype]}"
    )
    if llm.available():
        out = await llm.ask_json(SYSTEM_TURN.format(format=t["format"], lang_name=LANG[lang]["name"],
                                                    style=PRESSURE[pressure]["style"]), user)
        text = str(out.get("text", "")).strip()
    else:
        text = CLOSING[lang] if is_last else FALLBACK[lang].get(qtype, FALLBACK[lang]["intro"])
    return {"done": False, "speaker": mid, "title": m["title"], "voice": m["voice"],
            "qtype": qtype, "text": text, "closing": is_last, "index": idx, "total": len(order)}


SYSTEM_REPORT = """You are a senior interviewer giving honest, specific feedback after a mock interview. {format}
Write in {lang_name}, except JSON keys. Scores are integers 1-10. The transcript comes from speech recognition: ignore small spelling errors.
For each question: "verdict" judges the answer; "missing" names what a strong answer needed that the candidate did not say.
An empty answer means nothing was recorded; say so.
A short honest "I don't know" is acceptable in a real interview; say so in "verdict".
Return JSON:
{{"overall": int, "summary": str,
  "scores": {{{rubric}}},
  "answers": [{{"q": int, "verdict": str, "missing": str}}],
  "top_tips": [str, str, str],
  "prepare_next": [str, str, str, str, str]}}
prepare_next = 5 specific questions this candidate should prepare before the real interview, based on their dossier and weak spots."""


async def report(track: str, lang: str, dossier: dict, history: list[dict]) -> dict:
    t = TRACKS[track]
    out = {"delivery": delivery(lang, history)}
    answered = [h for h in history if h.get("answer")]
    if not answered:
        return out | {"overall": 0, "summary": "No answers recorded.", "scores": {}, "answers": [], "top_tips": [], "prepare_next": []}
    if not llm.available():
        return out | {"overall": 0, "summary": "Feedback needs GEMINI_API_KEY.", "scores": {}, "answers": [], "top_tips": [], "prepare_next": []}
    numbered = "\n".join(
        f"Q{i + 1} ({member(track, h['speaker'])['title']}): {h['question']}\nA{i + 1}: {h.get('answer') or '(no answer)'}"
        for i, h in enumerate(history)
    )
    rubric = ", ".join(f'"{r}": int' for r in t["rubric"])
    r = await llm.ask_json(SYSTEM_REPORT.format(format=t["format"], lang_name=LANG[lang]["name"], rubric=rubric),
                           f"Dossier: {_brief(dossier)}\n\nTranscript:\n{numbered}", temperature=0.3)
    better = await _restructure(lang, [h.get("answer", "") for h in history])
    for a in r.get("answers", []):
        q = a.get("q")
        a["better"] = better.get(q, "") if isinstance(q, int) else ""
    return out | r


SYSTEM_BETTER = """You rewrite spoken interview answers so they are clearer. You see ONLY the candidate's words, not the question.
For each answer: reorder and tighten the SAME points into 2-3 clean sentences in {lang_name}, first person.
Use only claims that are in that answer. Do not add any reason, motivation, cause-and-effect link, fact, number, name or example.
Remove fillers and repetition. If an answer has fewer than two real points, or is empty / "don't know", return "" for it.
Return JSON: {{"better": [{{"n": int, "text": str}}]}}"""


async def _restructure(lang: str, answers: list[str]) -> dict:
    items = [(i + 1, a) for i, a in enumerate(answers) if a and len(a.split()) >= SHORT_ANSWER_WORDS]
    if not items:
        return {}
    body = "\n".join(f"Answer {n}: {a}" for n, a in items)
    try:
        out = await llm.ask_json(SYSTEM_BETTER.format(lang_name=LANG[lang]["name"]), body, temperature=0.1)
    except llm.LLMError:
        return {}
    return {b["n"]: str(b.get("text", "")).strip() for b in out.get("better", []) if isinstance(b, dict) and isinstance(b.get("n"), int)}


# Offline fallback so the UI still works with no LLM key.
FALLBACK = {
    "en": {
        "intro": "Good morning. Please introduce yourself briefly.",
        "why": "Why do you want this role?",
        "resume": "Walk me through the most important thing on your resume.",
        "project": "Tell me about a project you are proud of and your own contribution.",
        "repo_file": "Pick one file in your project and explain what it does and why you wrote it that way.",
        "fundamentals": "Explain one core concept from your field that you use often.",
        "dsa": "How would you find the first repeated element in an array? Explain your approach and its complexity.",
        "scenario": "Your senior asks you to do something you think is wrong. What will you do?",
        "behavioral": "Tell me about a time you failed and what you learned.",
        "current": "What recent development in your field interests you, and why?",
        "case": "How many cups of tea are sold in Delhi in a day? Structure your estimate first.",
        "home": "What is the biggest problem in your home district?",
        "hobby": "Tell me more about one of your hobbies.",
    },
    "hi": {
        "intro": "नमस्कार, बैठिए। अपने बारे में संक्षेप में बताइए।",
        "why": "आप यह भूमिका क्यों चाहते हैं?",
        "resume": "अपने रिज़्यूमे की सबसे महत्वपूर्ण बात के बारे में बताइए।",
        "project": "अपने किसी प्रोजेक्ट के बारे में बताइए और उसमें आपका योगदान क्या था?",
        "repo_file": "अपने प्रोजेक्ट की किसी एक फ़ाइल के बारे में बताइए कि वह क्या करती है।",
        "fundamentals": "अपने क्षेत्र की कोई एक मूल अवधारणा समझाइए।",
        "dsa": "किसी array में पहला दोहराया गया तत्व कैसे ढूँढेंगे? तरीका और complexity बताइए।",
        "scenario": "मान लीजिए कोई वरिष्ठ आप पर गलत काम करने का दबाव डालता है। आप क्या करेंगे?",
        "behavioral": "किसी ऐसे समय के बारे में बताइए जब आप असफल हुए और आपने क्या सीखा।",
        "current": "हाल की कोई एक घटना बताइए जो आपके क्षेत्र के लिए महत्वपूर्ण है।",
        "case": "दिल्ली में एक दिन में कितने कप चाय बिकती है? पहले अपना ढाँचा बताइए।",
        "home": "आपके गृह जिले की सबसे बड़ी समस्या क्या है?",
        "hobby": "अपनी किसी एक रुचि के बारे में थोड़ा विस्तार से बताइए।",
    },
}
CLOSING = {
    "en": "Thank you. That brings us to the end of the interview. All the best.",
    "hi": "धन्यवाद। आपका साक्षात्कार समाप्त हुआ। शुभकामनाएँ।",
}
