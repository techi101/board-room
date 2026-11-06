"""Record the zero-credit demo once with real Gnani voices. Run: python -m tools.make_demo"""
import asyncio, json
from pathlib import Path
from backend import app as _  # loads .env
from backend import board, gnani
from backend.tracks import member

OUT = Path(__file__).resolve().parent.parent / "frontend" / "demo"
CANDIDATE_VOICE = "Shubham"
STEPS = [
    ("chair", "<pauses> नमस्कार, बैठिए। आपका DAF बताता है कि आप मुज़फ़्फ़रपुर से हैं और इंजीनियर हैं। इंजीनियरिंग छोड़कर प्रशासन क्यों?"),
    ("candidate", "सर, बाढ़ के समय मैंने देखा कि ज़िला प्रशासन ने राहत शिविर कैसे चलाए। इंजीनियर के रूप में मैं एक मशीन सुधार सकता हूँ, पर प्रशासन में रहकर पूरे ज़िले की व्यवस्था सुधार सकता हूँ।"),
    ("m1", "<whispers> दिलचस्प उत्तर है।"),
    ("m3", "आपने बाढ़ की बात की। अगर आप वहाँ के ज़िलाधिकारी होते, तो बाढ़ आने से पहले कौन से तीन काम करते?"),
    ("candidate", "पहला, तटबंधों की जाँच। दूसरा, गाँव स्तर पर चेतावनी की व्यवस्था। और तीसरा, मतलब, राहत सामग्री पहले से जमा करना।"),
    ("m4", "<clears throat> और अगर कोई स्थानीय नेता कहे कि राहत सबसे पहले उसके गाँव में पहुँचे, तब आप क्या करेंगे?"),
    ("candidate", "सर, मैं विनम्रता से मना करूँगा। राहत ज़रूरत के हिसाब से बँटेगी, और यह बात मैं लिखित में दर्ज करूँगा।"),
    ("chair", "धन्यवाद। आपका साक्षात्कार समाप्त हुआ। शुभकामनाएँ।"),
]

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    steps, history, q = [], [], None
    for i, (who, text) in enumerate(STEPS):
        voice = CANDIDATE_VOICE if who == "candidate" else member("upsc", who)["voice"]
        audio = await gnani.speak(text, voice, "hi-IN")
        name = f"s{i}.mp3"
        (OUT / name).write_bytes(audio)
        caption = board_strip(text)
        steps.append({"speaker": who, "caption": caption, "audio": name})
        if who == "candidate" and q:
            history.append({"speaker": q[0], "question": q[1], "answer": caption, "seconds": 18})
        elif who != "candidate" and "<whispers>" not in text:
            q = (who, caption)
    rep = await board.report("upsc", "hi", {"fields": {"home": "Bihar, Muzaffarpur", "graduation": "B.Tech"}}, history)
    (OUT / "demo.json").write_text(json.dumps({"track": "upsc", "lang": "hi", "steps": steps, "history": history, "report": rep},
                                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("demo written:", len(steps), "clips,", len(history), "answers, overall", rep.get("overall"))

def board_strip(t):
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()

asyncio.run(main())
