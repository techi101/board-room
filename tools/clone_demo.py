"""Re-voice the candidate's answers in a demo with a cloned voice.

Run: python -m tools.clone_demo <demo dir under frontend/demo, "" for Hindi> <embedding.json> <hi-IN|en-IN>
The embedding comes from the builder's own recorded sample and stays outside the repo.
"""
import asyncio, json, sys
from pathlib import Path
from backend import app as _  # loads .env
from backend import gnani

BASE = Path(__file__).resolve().parent.parent / "frontend" / "demo"
LABEL = "Candidate · AI clone of the builder's voice"


async def main(sub: str, emb_path: str, code: str):
    out = BASE / sub if sub else BASE
    data = json.loads((out / "demo.json").read_text(encoding="utf-8"))
    emb = json.loads(Path(emb_path).read_text())
    n = 0
    for i, step in enumerate(data["steps"]):
        if step["speaker"] != "candidate":
            continue
        audio = await gnani.speak_cloned(step["caption"], emb, code, "mp3")
        name = f"c{i}.mp3"
        (out / name).write_bytes(audio)
        old = out / Path(step["audio"]).name
        if old.exists() and old.name != name:
            old.unlink()
        step["audio"] = (out / name).relative_to(BASE).as_posix()
        n += 1
    data["candidate_label"] = LABEL
    (out / "demo.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{sub or 'hi'}: {n} answers re-voiced")


asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
