# Board Room: plan (6 Nov 2026)

## Goal
A voice mock-interview panel for any career path, in Hindi or English, built on Gnani Prisma (STT) + Timbre (TTS) + voice clone.
Presented UPSC-first (the hook), but it handles software placements, core engineering/PSU, CA, MBA PI, bank PO, consulting, and any custom role.

## How real interviews run (research summary)
| Track | Real format | Panel we model |
|---|---|---|
| Civil services (UPSC/State PSC) | 5-member board, DAF-based, ~25-30 min, Hindi or English | Chair + 4 members |
| Software (campus/off-campus) | OA, then CS fundamentals (OS/CN/DBMS/OOP), DSA, project deep-dive, HR | HR, Tech Lead (project + repo files), Senior Engineer (fundamentals + DSA approach), Eng Manager (scenario/behavioural) |
| Core engg / PSU | Branch fundamentals, final-year project, HR/situational | Domain expert, Project guide, HR |
| CA articleship / fresher / Big 4 | Accounting Standards, SAs, CARO 2020, Income Tax/TDS, GST, practical audit scenarios, articleship work, HR | Audit Partner, Tax Manager, Finance Head, HR |
| MBA PI (IIM style) | 15-20 min, 2-3 panelists, intro + why MBA, academics (freshers), work-ex, current affairs | Chair professor, Faculty, Alumnus |
| Bank PO / RBI | 4-5 member panel, background, banking awareness (repo rate, UPI), current affairs, situational (angry customer, cyber fraud, NPA) | Chair GM, Banking expert, HR, Psychologist |
| Consulting / analyst | Case + guesstimate, fit | Engagement Manager, Partner |
| Custom (paste any JD) | Generic hiring-manager / domain / HR loop | Hiring Manager, Domain Expert, HR |

## What the panel knows (intake)
- Resume PDF (Gemini reads it) or pasted text
- GitHub repo or profile URL: we fetch the tree, README, manifest and the 6 most central code files, then extract file-level facts so questions name real files ("In `backend/auth.py` you hash with SHA-256; why not bcrypt?")
- Job description / target role
- Track-specific fields (DAF for UPSC; CA level; etc.)
- The candidate SEES the dossier before starting (transparency, can catch wrong facts)

## Limitations and how we handle them
| Limitation | Mitigation |
|---|---|
| 5,000 free Gnani credits, unknown per-call price | Disk cache for repeated TTS; per-IP daily caps; global daily TTS character budget; auto fallback to browser voice + typing when budget is hit; zero-credit recorded demo for visitors |
| Reported 1 active request per key (429) | Server semaphore + retry with backoff |
| STT REST max 60 s | Browser splits answers into 50 s WAV chunks |
| Voice clone cannot stream / no tags / 1 sentence | Clone used only for end-of-interview replay, sentence by sentence |
| LLM may invent facts about the candidate or repo | Questions grounded in the dossier only; repo questions must cite a fetched file; feedback "better answer" may only reuse the candidate's own points, else left empty |
| Coding rounds need an editor | DSA asked as "explain your approach and complexity aloud"; stated in README |
| GitHub API 60 req/hr unauthenticated | ~3 API calls per repo (raw files are separate); optional GITHUB_TOKEN |
| Gemini model churn / overload | Model fallback list |
| Mic needs HTTPS | Deployed on HTTPS host |
| Privacy (resume, voice) | Nothing stored server-side; clone needs explicit consent; "AI voice" label |
| Legal (UPSC name) | Product name is Board Room; "Not affiliated with UPSC or any recruiter" |
| STT transcripts may clean fillers | Delivery metrics (wpm, fillers) labelled approximate |

## Extra features
Pressure level (friendly / standard / stress), delivery metrics (words per minute, filler words, long answers), printable report, own-voice replay, demo mode.

## Engagement plan (shortlist = engagement on the nominated post)
- Post 8 Nov evening (gives 2 days of engagement before 10 Nov 11:59 PM)
- Hook: real Vajiram year + "I let an AI panel grill me on my own GitHub repo"
- 60 s video: Hindi UPSC board whisper moment, then repo-file question, then own-voice replay
- CTA that earns real comments: "Comment your target role (UPSC / SDE / CA / MBA / bank PO)"; reply to every comment
- Native video, link in first comment, tag Gnani; ask classmates/clubs for genuine comments (no engagement swaps)
