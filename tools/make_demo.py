"""Record the zero-credit demos once with real Gnani voices. Run: python -m tools.make_demo [hi|en]"""
import asyncio, json, sys
from pathlib import Path
from backend import app as _  # loads .env
from backend import board, gnani
from backend.tracks import member

BASE = Path(__file__).resolve().parent.parent / "frontend" / "demo"
STEPS_HI = [
    ("chair", "<pauses> नमस्कार, बैठिए। आपका DAF बताता है कि आप इलाहाबाद से हैं और इंजीनियर हैं। इंजीनियरिंग छोड़कर प्रशासन क्यों?"),
    ("candidate", "सर, बाढ़ के समय मैंने देखा कि ज़िला प्रशासन ने राहत शिविर कैसे चलाए। इंजीनियर के रूप में मैं एक मशीन सुधार सकता हूँ, पर प्रशासन में रहकर पूरे ज़िले की व्यवस्था सुधार सकता हूँ।"),
    ("m1", "<whispers> दिलचस्प उत्तर है।"),
    ("m3", "आपने बाढ़ की बात की। अगर आप वहाँ के ज़िलाधिकारी होते, तो बाढ़ आने से पहले कौन से तीन काम करते?"),
    ("candidate", "पहला, तटबंधों की जाँच। दूसरा, गाँव स्तर पर चेतावनी की व्यवस्था। और तीसरा, मतलब, राहत सामग्री पहले से जमा करना।"),
    ("m4", "<clears throat> और अगर कोई स्थानीय नेता कहे कि राहत सबसे पहले उसके गाँव में पहुँचे, तब आप क्या करेंगे?"),
    ("candidate", "सर, मैं विनम्रता से मना करूँगा। राहत ज़रूरत के हिसाब से बँटेगी, और यह बात मैं लिखित में दर्ज करूँगा।"),
    ("chair", "धन्यवाद। आपका साक्षात्कार समाप्त हुआ। शुभकामनाएँ।"),
]

# English: a campus software interview built on a real repo (techi101/launchswitch).
STEPS_EN = [
    ("hr", "Hi, welcome, please take a seat. Tell me briefly about something you built recently that you are proud of."),
    ("candidate", "I built LaunchSwitch, a feature flag service. A team can switch a new feature on for five percent of users, watch it, and roll it back in one click. It runs on Node with SQLite and is deployed on Vercel."),
    ("lead", "I opened your repo. In your api folder, index.js points the database to the tmp folder. On Vercel, what happens to that file when the function goes cold?"),
    ("candidate", "Um, it gets wiped. The tmp folder only lives as long as that instance, so the flags could reset. For a demo that was fine, but in production I would move it to a hosted database like Postgres."),
    ("senior", "<whispers> Good. He knows the limitation."),
    ("senior", "Your rollout is a percentage. How do you make sure the same user always gets the same answer?"),
    ("candidate", "I hash the user ID together with the flag key, take it modulo one hundred, and compare that with the rollout percentage. Same input, same bucket, so it is deterministic."),
    ("em", "<clears throat> Last one. It is Friday evening and a flag you shipped breaks checkout. What do you do?"),
    ("candidate", "First I turn the flag off, because that is the whole point of a flag. Then I tell the team, check the logs, and write a short note on what went wrong before I fix it properly."),
    ("hr", "Thank you, that is all from our side. All the best."),
]

# English UPSC board: same story as the Hindi demo.
STEPS_UPSC_EN = [
    ("chair", "<pauses> Good morning, please sit down. Your DAF says you are from Allahabad and an engineer. Why leave engineering for administration?"),
    ("candidate", "Sir, during the floods I saw how the district administration ran the relief camps. As an engineer I can fix one machine, but in administration I can fix how a whole district works."),
    ("m1", "<whispers> Interesting answer."),
    ("m3", "You mentioned floods. If you were the District Magistrate there, what three things would you do before the floods arrive?"),
    ("candidate", "First, inspect the embankments. Second, set up a village level warning system. And third, um, stock relief material in advance."),
    ("m4", "<clears throat> And if a local politician insists that relief must reach his village first, what will you do?"),
    ("candidate", "Sir, I will politely refuse. Relief will be distributed by need, and I will put that decision on record in writing."),
    ("chair", "Thank you. Your interview is over. All the best."),
]

DEMOS = {
    "upsc_en": dict(track="upsc", lang="en", code="en-IN", out=BASE / "upsc_en", candidate="Shubham", steps=STEPS_UPSC_EN,
                    dossier={"fields": {"home": "Uttar Pradesh, Allahabad", "graduation": "B.Tech"}}),
    "hi": dict(track="upsc", lang="hi", code="hi-IN", out=BASE, candidate="Shubham", steps=STEPS_HI,
               dossier={"fields": {"home": "Uttar Pradesh, Allahabad", "graduation": "B.Tech"}}),
    "software_en": dict(track="software", lang="en", code="en-IN", out=BASE / "software_en", candidate="Devansh", steps=STEPS_EN,
               dossier={"fields": {"role": "SDE intern"}, "repo": "techi101/launchswitch"}),
}

async def main(key):
    D = DEMOS[key]
    OUT = D["out"]
    OUT.mkdir(parents=True, exist_ok=True)
    steps, history, q = [], [], None
    for i, (who, text) in enumerate(D["steps"]):
        voice = D["candidate"] if who == "candidate" else member(D["track"], who)["voice"]
        audio = await gnani.speak(text, voice, D["code"])
        name = f"s{i}.mp3"
        (OUT / name).write_bytes(audio)
        caption = board_strip(text)
        steps.append({"speaker": who, "caption": caption, "audio": (OUT / name).relative_to(BASE).as_posix()})
        if who == "candidate" and q:
            history.append({"speaker": q[0], "question": q[1], "answer": caption, "seconds": 18})
        elif who != "candidate" and "<whispers>" not in text:
            q = (who, caption)
    rep = await board.report(D["track"], D["lang"], D["dossier"], history)
    (OUT / "demo.json").write_text(json.dumps({"track": D["track"], "lang": D["lang"], "steps": steps, "history": history, "report": rep},
                                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("demo written:", len(steps), "clips,", len(history), "answers, overall", rep.get("overall"))

def board_strip(t):
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()

asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "hi"))
