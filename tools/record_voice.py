"""Record a voice sample for cloning, in its own window. Run: python tools/record_voice.py en|hi"""
import os, sys, time, wave
import numpy as np
import sounddevice as sd

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
SECONDS = 30
RATE = 16000
DL = os.path.expanduser("~/Downloads")
OUT = os.path.join(DL, f"my_voice_{LANG}.wav")
script = open(os.path.join(DL, f"voice_script_{LANG}.txt"), encoding="utf-8-sig").read().split("\n\n", 1)[-1].strip()

os.system("")  # enable colours on Windows
print("\n  BOARD ROOM  |  voice sample (" + ("English" if LANG == "en" else "Hindi") + ")\n")
print("  Read this at your normal interview pace:\n")
print("  " + script + "\n")
print("  Tip: quiet room, fan off, about 30 cm from the laptop.\n")
input("  Press ENTER when ready. Recording starts after a 3 second countdown...")
for i in (3, 2, 1):
    print(f"  {i}...", flush=True); time.sleep(1)
print("\n  >>> RECORDING. Speak now. Press Ctrl+C to stop early (or it stops at 30 s).\n", flush=True)

frames = []
def cb(indata, n, t, status):
    frames.append(indata.copy())

start = time.time()
try:
    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", callback=cb):
        while time.time() - start < SECONDS:
            if frames:
                lvl = int(min(1, np.abs(frames[-1]).mean() / 3000) * 30)
                print(f"\r  {int(time.time() - start):2d}s  [{'#' * lvl:<30}]", end="", flush=True)
            time.sleep(0.1)
except KeyboardInterrupt:
    pass

audio = np.concatenate(frames) if frames else np.zeros((0, 1), "int16")
with wave.open(OUT, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(audio.tobytes())
peak = int(np.abs(audio).max()) if len(audio) else 0
print(f"\n\n  Saved {OUT}  ({len(audio) / RATE:.1f} s, peak level {peak})")
print("  " + ("Looks good." if peak > 3000 else "Very quiet. Move closer to the mic and record again."))
input("\n  Press ENTER to close this window.")
