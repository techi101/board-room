"""Interview tracks: who sits on the panel, what each asks, and how answers are scored.

Formats are modelled on how these interviews actually run in India (see PLAN.md).
Voices are Gnani Timbre v3.0 (every voice speaks all 10 languages).
"""

QTYPES = {
    "intro": "Open the interview: greet briefly and ask the candidate to introduce themselves, tied to their profile.",
    "why": "Probe motivation: why this career, role or organisation. Push back gently if the answer is generic.",
    "resume": "Pick ONE specific claim from the dossier (a role, achievement, skill or number) and probe whether they really did it and how.",
    "project": "Deep-dive into ONE project from the dossier: their own contribution, a design choice, a trade-off, or what went wrong.",
    "repo_file": "Ask about ONE specific fact from the dossier's repo facts and NAME the file path in the question. If there are no repo facts, ask a project deep-dive instead.",
    "fundamentals": "Ask ONE core concept question from this track's fundamentals, linked to something the candidate used or studied if possible.",
    "dsa": "Give a small data-structures/algorithms problem in one or two sentences and ask them to explain their approach and time complexity aloud. No code.",
    "scenario": "Give a realistic on-the-job situation for this role and ask what they would do and why.",
    "behavioral": "Ask a behavioural question (conflict, failure, pressure, leadership) and expect a specific past example.",
    "current": "Ask about a significant recent development relevant to this field, and their view on it. Avoid exact dates you are unsure of.",
    "case": "Give a short business case or guesstimate in 2-3 sentences and ask them to first lay out how they would structure it.",
    "home": "Ask about their home state/district: an issue, an opportunity, or what they would do as an officer there.",
    "hobby": "Ask about a hobby or extra-curricular from the dossier, going one level deeper than small talk.",
    "closing": "Close the interview politely in one or two sentences. Do not ask a question.",
}

TRACKS = {
    "upsc": {
        "name": "Civil Services Board", "tag": "UPSC / State PSC personality test",
        "langs": ["hi", "en"],
        "format": "A five-member civil services personality test board. Calm, dignified, probing; tests balance, honesty, awareness and administrative judgement, using the DAF.",
        "fundamentals": "Indian polity, governance, economy, ethics, the candidate's graduation and optional subjects",
        "panel": [
            {"id": "chair", "title": "Chairperson", "voice": "Avinash", "focus": "DAF background, motivation, integrity and ethics"},
            {"id": "m1", "title": "Member 1", "voice": "Riyaa", "focus": "current affairs, international relations and economy"},
            {"id": "m2", "title": "Member 2", "voice": "Prakash", "focus": "graduation and optional subject, science and technology"},
            {"id": "m3", "title": "Member 3", "voice": "Kalpana", "focus": "home state and district, society, governance"},
            {"id": "m4", "title": "Member 4", "voice": "Devansh", "focus": "hobbies and situational questions an officer faces"},
        ],
        "plans": {
            "short": [("chair", "intro"), ("m1", "current"), ("m2", "fundamentals"), ("m3", "home"), ("m4", "scenario"), ("chair", "closing")],
            "full": [("chair", "intro"), ("chair", "why"), ("m1", "current"), ("m1", "current"), ("m2", "fundamentals"), ("m2", "resume"),
                     ("m3", "home"), ("m3", "fundamentals"), ("m4", "hobby"), ("m4", "scenario"), ("chair", "closing")],
        },
        "rubric": ["clarity", "honesty", "balance", "knowledge", "composure"],
        "fields": ["home", "graduation", "optional", "hobbies", "other"],
    },
    "software": {
        "name": "Software Engineer", "tag": "Campus / off-campus SDE, intern or new grad",
        "langs": ["en", "hi"],
        "format": "A software engineering interview loop for a fresher: CS fundamentals, DSA reasoning, a deep project and code discussion, and behavioural fit.",
        "fundamentals": "OOP, DBMS and SQL, operating systems, computer networks, the languages and frameworks on their resume",
        "panel": [
            {"id": "hr", "title": "HR Partner", "voice": "Shivani", "focus": "introduction, motivation, culture fit"},
            {"id": "lead", "title": "Tech Lead", "voice": "Shubham", "focus": "their projects and GitHub code, design choices"},
            {"id": "senior", "title": "Senior Engineer", "voice": "Riyaa", "focus": "CS fundamentals and DSA reasoning"},
            {"id": "em", "title": "Engineering Manager", "voice": "Avinash", "focus": "scenarios, ownership, teamwork"},
        ],
        "plans": {
            "short": [("hr", "intro"), ("lead", "project"), ("lead", "repo_file"), ("senior", "fundamentals"), ("senior", "dsa"), ("em", "scenario"), ("hr", "closing")],
            "full": [("hr", "intro"), ("lead", "project"), ("lead", "repo_file"), ("lead", "repo_file"), ("senior", "fundamentals"), ("senior", "fundamentals"),
                     ("senior", "dsa"), ("em", "scenario"), ("em", "behavioral"), ("hr", "why"), ("hr", "closing")],
        },
        "rubric": ["technical_depth", "project_ownership", "problem_solving", "communication", "culture_fit"],
        "fields": ["role", "github", "other"],
    },
    "core": {
        "name": "Core Engineering / PSU", "tag": "ECE, EE, Mech, Civil, Chem; PSU and core jobs",
        "langs": ["en", "hi"],
        "format": "A core engineering / PSU technical interview: branch fundamentals, final-year project, and situational HR.",
        "fundamentals": "the candidate's engineering branch fundamentals (e.g. ECE: signals, analog/digital, communication; Mech: thermodynamics, SOM; Civil: structures, RCC)",
        "panel": [
            {"id": "expert", "title": "Domain Expert", "voice": "Prakash", "focus": "branch fundamentals"},
            {"id": "guide", "title": "Project Reviewer", "voice": "Lakshmi", "focus": "final-year project and internships"},
            {"id": "hr", "title": "HR Head", "voice": "Avinash", "focus": "motivation, situations, values"},
        ],
        "plans": {
            "short": [("hr", "intro"), ("expert", "fundamentals"), ("expert", "fundamentals"), ("guide", "project"), ("hr", "scenario"), ("hr", "closing")],
            "full": [("hr", "intro"), ("expert", "fundamentals"), ("expert", "fundamentals"), ("expert", "fundamentals"), ("guide", "project"),
                     ("guide", "repo_file"), ("guide", "resume"), ("hr", "scenario"), ("hr", "why"), ("hr", "behavioral"), ("hr", "closing")],
        },
        "rubric": ["fundamentals", "project_understanding", "practical_thinking", "communication", "attitude"],
        "fields": ["role", "graduation", "github", "other"],
    },
    "ca": {
        "name": "Chartered Accountancy", "tag": "CA articleship, CA fresher, Big 4",
        "langs": ["en", "hi"],
        "format": "A CA articleship / fresher / Big 4 interview. Leans on practical situations over theory; rewards honest 'I don't know' plus reasoning.",
        "fundamentals": "Accounting Standards and Ind AS, Standards on Auditing, CARO 2020, Schedule III, Income Tax and TDS, GST",
        "panel": [
            {"id": "partner", "title": "Audit Partner", "voice": "Avinash", "focus": "statutory audit, SAs, CARO, audit situations"},
            {"id": "tax", "title": "Tax Manager", "voice": "Kalpana", "focus": "GST, income tax, TDS"},
            {"id": "fin", "title": "Finance Head", "voice": "Prakash", "focus": "accounting standards, Ind AS, financial statements"},
            {"id": "hr", "title": "HR", "voice": "Chetana", "focus": "motivation, articleship experience, firm fit"},
        ],
        "plans": {
            "short": [("hr", "intro"), ("partner", "scenario"), ("tax", "fundamentals"), ("fin", "fundamentals"), ("hr", "why"), ("hr", "closing")],
            "full": [("hr", "intro"), ("hr", "resume"), ("partner", "scenario"), ("partner", "fundamentals"), ("tax", "fundamentals"), ("tax", "scenario"),
                     ("fin", "fundamentals"), ("fin", "current"), ("hr", "behavioral"), ("hr", "why"), ("hr", "closing")],
        },
        "rubric": ["technical_accuracy", "practical_application", "exposure", "communication", "professional_attitude"],
        "fields": ["role", "ca_level", "other"],
    },
    "mba": {
        "name": "MBA Personal Interview", "tag": "IIM / B-school PI",
        "langs": ["en", "hi"],
        "format": "A 15-20 minute B-school personal interview with a small faculty panel: intro and why MBA, academics (especially for freshers), work experience, current affairs.",
        "fundamentals": "the candidate's graduation subjects, basic economics and business",
        "panel": [
            {"id": "chair", "title": "Panel Chair", "voice": "Harshad", "focus": "introduction, why MBA, goals"},
            {"id": "faculty", "title": "Faculty Member", "voice": "Lakshmi", "focus": "academics and current affairs"},
            {"id": "alum", "title": "Alumnus", "voice": "Devansh", "focus": "work experience, situations, hobbies"},
        ],
        "plans": {
            "short": [("chair", "intro"), ("chair", "why"), ("faculty", "fundamentals"), ("faculty", "current"), ("alum", "scenario"), ("chair", "closing")],
            "full": [("chair", "intro"), ("chair", "why"), ("faculty", "fundamentals"), ("faculty", "fundamentals"), ("faculty", "current"),
                     ("alum", "resume"), ("alum", "hobby"), ("alum", "scenario"), ("chair", "behavioral"), ("chair", "why"), ("chair", "closing")],
        },
        "rubric": ["clarity_of_goals", "academic_grounding", "awareness", "communication", "poise"],
        "fields": ["graduation", "hobbies", "other"],
    },
    "bank": {
        "name": "Bank PO / RBI", "tag": "IBPS PO, SBI PO, RBI Grade B",
        "langs": ["hi", "en"],
        "format": "A public sector bank interview panel: background, banking and financial awareness (basic but precise), current affairs, and situational judgement.",
        "fundamentals": "banking awareness: repo rate, CRR/SLR, NPAs, UPI, KYC, financial inclusion schemes",
        "panel": [
            {"id": "chair", "title": "Chairperson (GM)", "voice": "Avinash", "focus": "background and motivation"},
            {"id": "banker", "title": "Banking Expert", "voice": "Prakash", "focus": "banking and financial awareness"},
            {"id": "hr", "title": "HR Officer", "voice": "Shivani", "focus": "personality and values"},
            {"id": "psy", "title": "Psychologist", "voice": "Chetana", "focus": "situational judgement and pressure"},
        ],
        "plans": {
            "short": [("chair", "intro"), ("banker", "fundamentals"), ("banker", "current"), ("psy", "scenario"), ("hr", "why"), ("chair", "closing")],
            "full": [("chair", "intro"), ("chair", "home"), ("banker", "fundamentals"), ("banker", "fundamentals"), ("banker", "current"),
                     ("psy", "scenario"), ("psy", "scenario"), ("hr", "resume"), ("hr", "hobby"), ("hr", "why"), ("chair", "closing")],
        },
        "rubric": ["banking_awareness", "current_affairs", "situational_judgement", "communication", "confidence"],
        "fields": ["home", "graduation", "hobbies", "other"],
    },
    "consulting": {
        "name": "Consulting / Analyst", "tag": "Case interviews, guesstimates, product/business analyst",
        "langs": ["en", "hi"],
        "format": "A consulting / analyst interview: structured case and guesstimate, then fit questions.",
        "fundamentals": "business frameworks, unit economics, basic statistics",
        "panel": [
            {"id": "em", "title": "Engagement Manager", "voice": "Yashraj", "focus": "case and guesstimate"},
            {"id": "partner", "title": "Partner", "voice": "Riyaa", "focus": "fit, motivation, leadership"},
        ],
        "plans": {
            "short": [("partner", "intro"), ("em", "case"), ("em", "case"), ("partner", "behavioral"), ("partner", "closing")],
            "full": [("partner", "intro"), ("partner", "why"), ("em", "case"), ("em", "case"), ("em", "case"), ("em", "fundamentals"),
                     ("partner", "resume"), ("partner", "behavioral"), ("partner", "scenario"), ("partner", "closing")],
        },
        "rubric": ["structure", "quantitative", "business_sense", "communication", "fit"],
        "fields": ["role", "other"],
    },
    "custom": {
        "name": "Any Role (paste JD)", "tag": "Sales, teaching, design, marketing, nursing, anything",
        "langs": ["en", "hi"],
        "format": "A realistic interview for the role in the job description, as it would be run in India.",
        "fundamentals": "the core skills named in the job description",
        "panel": [
            {"id": "hm", "title": "Hiring Manager", "voice": "Avinash", "focus": "role fit, past work, scenarios"},
            {"id": "expert", "title": "Domain Expert", "voice": "Lakshmi", "focus": "skills from the job description"},
            {"id": "hr", "title": "HR", "voice": "Shivani", "focus": "motivation and behaviour"},
        ],
        "plans": {
            "short": [("hr", "intro"), ("hm", "resume"), ("expert", "fundamentals"), ("hm", "scenario"), ("hr", "behavioral"), ("hr", "closing")],
            "full": [("hr", "intro"), ("hm", "resume"), ("hm", "project"), ("expert", "fundamentals"), ("expert", "fundamentals"),
                     ("expert", "scenario"), ("hm", "scenario"), ("hm", "current"), ("hr", "behavioral"), ("hr", "why"), ("hr", "closing")],
        },
        "rubric": ["role_skills", "relevant_experience", "judgement", "communication", "motivation"],
        "fields": ["role", "github", "other"],
    },
}


def member(track: str, mid: str) -> dict:
    return next(m for m in TRACKS[track]["panel"] if m["id"] == mid)


def public() -> dict:
    """What the browser needs to render track cards, forms and panels."""
    return {
        k: {"name": t["name"], "tag": t["tag"], "langs": t["langs"], "fields": t["fields"],
            "panel": [{"id": m["id"], "title": m["title"], "voice": m["voice"]} for m in t["panel"]],
            "lengths": {p: len(v) for p, v in t["plans"].items()}}
        for k, t in TRACKS.items()
    }
