# Board Room

**Sit in front of a real-sounding interview panel and answer out loud, in Hindi or English.**
The panel reads your resume, your GitHub code and your target role, then asks you the questions a real panel would.

Built for the Gnani.ai Great Indian AI Internship Challenge on **Gnani Prisma** (speech-to-text), **Gnani Timbre v3.0** (expressive voices) and **Gnani voice cloning**.

Live: **LIVE_URL** · 1-minute demo button on the home page (pre-recorded, uses no credits)

> Practice tool. Not affiliated with UPSC, any recruiter or any government body.

## Why
I spent a year in UPSC coaching at Vajiram & Ravi in Delhi. Mock interviews were the one thing you could not practise alone: a good one needs a panel, costs money, and in Hindi medium there are even fewer. Placement interviews have the same problem: you get grilled on your own project code, and nobody practises that until the real day.

## What it does
1. **Pick your interview.** 8 tracks, each modelled on how that interview really runs in India:

   | Track | Panel |
   |---|---|
   | Civil Services Board (UPSC / State PSC) | Chairperson + 4 members, DAF-based |
   | Software Engineer (campus / off-campus) | HR, Tech Lead, Senior Engineer, Engineering Manager |
   | Core Engineering / PSU | Domain Expert, Project Reviewer, HR |
   | Chartered Accountancy (articleship, Big 4) | Audit Partner, Tax Manager, Finance Head, HR |
   | MBA Personal Interview | Panel Chair, Faculty, Alumnus |
   | Bank PO / RBI | Chairperson, Banking Expert, HR, Psychologist |
   | Consulting / Analyst | Engagement Manager, Partner |
   | Any role (paste a JD) | Hiring Manager, Domain Expert, HR |

2. **Brief the panel.** Upload your resume PDF, give a GitHub repo or profile, paste a JD. The app reads the repo tree, README, manifest and the 6 most central code files, and turns them into **code facts tied to real file paths**. You see exactly what the panel knows before you start.
3. **Face the panel.** Each member has their own Gnani voice. Questions follow the real format: intro, motivation, resume claims, project deep-dive, **questions about a specific file in your repo**, fundamentals, DSA reasoning, scenarios, current affairs, cases. Members follow up when an answer is vague.
4. **It feels like a room.** Members whisper to each other, sigh at one-line answers, and the chair cuts you off when you ramble (Gnani Timbre audio tags). Three moods: friendly, standard, stress interview.
5. **Get feedback.** Scores on a track-specific rubric, a verdict and "what was missing" per question, 5 questions to prepare next, and how you spoke (pace, filler words, answer length). Save as PDF.
6. **Hear yourself do better.** Optional: record 20 seconds, and your better-structured answers play back **in your own cloned voice**.

## How it works
```
Browser (mic -> 16 kHz WAV, 50 s chunks)
   |  /api/stt  -> Gnani Prisma v2.5 (hi-IN / en-IN)
   |  /api/turn -> Gemini writes ONE panel member's next line from: track format + dossier + transcript
   |  /api/tts  -> Gnani Timbre v3.0 (13 voices, audio tags) -> cached mp3
   |  /api/report -> rubric + verdicts; "better answer" rewritten from the candidate's words only
   |  /api/clone/* -> Gnani vachana-vc-v1 embedding + cloned speech, one sentence at a time
FastAPI (stateless; the browser holds the session) on Vercel
```

## Honest design choices
- **Rule-based where it should be.** Interruptions, sighs, whispers and speaking metrics are fixed rules, labelled as such in the UI. Only question wording and feedback come from the LLM.
- **No invented facts.** Personal questions may only use the dossier. Repo facts that cite a file the app did not actually read are dropped. The "better answer" is written in a separate step that sees **only the candidate's own words**, never the question or resume, so it cannot borrow claims from them.
- **Coding rounds are verbal.** DSA questions ask for approach and complexity aloud; there is no code editor.
- **The voice clone is end-only.** It cannot stream and ignores audio tags, so it is used for replay, sentence by sentence, with explicit consent and an "AI voice" label.

## Protecting the free credits
5,000 free Gnani credits had to survive a public link:
- every TTS line is cached on disk, so repeats are free; the home-page demo is pre-recorded;
- per-visitor daily caps and a global daily character / listening budget;
- a "save credits" switch uses the browser's own voice;
- when any budget is hit, the app falls back to browser voice + typing instead of breaking.

## Privacy
Resume, repo contents and voice are used only for the live session and are not stored on the server.

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env   # add GNANI_API_KEY and GEMINI_API_KEY
uvicorn backend.app:app --reload
python -m pytest -q    # 21 tests
```
Without keys the app still runs: browser voice, typed answers and fixed questions.
