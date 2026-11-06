"""Build the candidate dossier: resume (PDF or text), GitHub repo facts, job description, form fields.

The dossier is the ONLY thing the panel is allowed to ask personal questions from,
and it is shown to the candidate before the interview starts.
"""
import base64
import os
import re

import httpx

from . import llm

GH_API = "https://api.github.com"
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".cc", ".c", ".h", ".cs",
            ".kt", ".swift", ".rb", ".php", ".dart", ".scala", ".sql", ".m", ".vue", ".svelte", ".sol"}
SKIP_DIRS = {"node_modules", "dist", "build", "vendor", ".venv", "venv", "env", "__pycache__", "migrations",
             ".next", "coverage", "target", "bin", "obj", ".github", "docs", "examples", "assets", "static", "public"}
KEY_NAMES = {"main", "app", "index", "server", "api", "routes", "model", "models", "train", "core", "engine",
             "service", "services", "handler", "controller", "agent", "pipeline", "utils", "db", "auth", "views"}
MANIFESTS = {"package.json", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle", "go.mod", "Cargo.toml"}
MAX_FILES = 6
MAX_CHARS = 3500


class ContextError(RuntimeError):
    pass


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "board-room-interview-app"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return h


def parse_github(url: str) -> tuple[str, str | None]:
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9-]+)(?:/([A-Za-z0-9._-]+))?/?", url.strip())
    if not m:
        raise ContextError("Not a GitHub URL. Use github.com/<user> or github.com/<user>/<repo>.")
    repo = m.group(2)
    if repo and repo.endswith(".git"):
        repo = repo[:-4]
    return m.group(1), repo


def score_path(path: str, size: int) -> float:
    parts = path.split("/")
    if any(p in SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
        return -1
    name = parts[-1]
    stem, dot, ext = name.rpartition(".")
    ext = "." + ext if dot else ""
    low = name.lower()
    if ext not in CODE_EXT or ".min." in low or "test" in low or "spec" in low or "config" in low:
        return -1
    if size < 300 or size > 60000:
        return -1
    s = 1.0
    if stem.lower() in KEY_NAMES:
        s += 3
    if any(p in ("src", "app", "backend", "server", "api", "lib", "core") for p in parts[:-1]):
        s += 1
    s -= 0.4 * max(0, len(parts) - 3)
    s += min(size, 15000) / 15000
    return s


def pick_files(tree: list[dict]) -> tuple[str | None, str | None, list[str]]:
    blobs = [t for t in tree if t.get("type") == "blob"]
    readme = next((t["path"] for t in blobs if t["path"].lower() in ("readme.md", "readme.rst", "readme.txt", "readme")), None)
    manifest = next((t["path"] for t in blobs if t["path"] in MANIFESTS), None)
    scored = sorted(((score_path(t["path"], t.get("size", 0)), t["path"]) for t in blobs), reverse=True)
    code = [p for s, p in scored if s > 0][:MAX_FILES]
    return readme, manifest, code


async def fetch_repo(url: str) -> dict:
    owner, repo = parse_github(url)
    async with httpx.AsyncClient(timeout=20, headers=_gh_headers(), follow_redirects=True) as c:
        if not repo:
            r = await c.get(f"{GH_API}/users/{owner}/repos", params={"sort": "pushed", "per_page": 30})
            if r.status_code != 200:
                raise ContextError(f"GitHub user not found or rate-limited ({r.status_code}).")
            repos = [x for x in r.json() if not x.get("fork") and x.get("size", 0) > 0]
            if not repos:
                raise ContextError("No public non-fork repos found on that profile.")
            repos.sort(key=lambda x: (x.get("stargazers_count", 0), x.get("pushed_at", "")), reverse=True)
            repo = repos[0]["name"]
        meta = await c.get(f"{GH_API}/repos/{owner}/{repo}")
        if meta.status_code != 200:
            raise ContextError(f"Repo {owner}/{repo} not found or private ({meta.status_code}).")
        meta = meta.json()
        branch = meta.get("default_branch", "main")
        tr = await c.get(f"{GH_API}/repos/{owner}/{repo}/git/trees/{branch}", params={"recursive": "1"})
        if tr.status_code != 200:
            raise ContextError(f"Could not read the file tree ({tr.status_code}).")
        tree = tr.json().get("tree", [])
        readme, manifest, code = pick_files(tree)
        files = {}
        for path in [p for p in [readme, manifest] if p] + code:
            raw = await c.get(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}")
            if raw.status_code == 200:
                files[path] = raw.text[:MAX_CHARS]
    return {
        "name": f"{owner}/{repo}", "url": f"https://github.com/{owner}/{repo}",
        "description": meta.get("description") or "", "language": meta.get("language") or "",
        "file_count": sum(1 for t in tree if t.get("type") == "blob"), "files": files,
    }


SYSTEM_DOSSIER = """You prepare an interviewer's briefing about a candidate. Use ONLY the material given.
Never invent anything. Keep every item short and specific. Write in English.
Return JSON:
{"summary": str (2 sentences),
 "education": [str], "experience": [str], "skills": [str],
 "projects": [{"name": str, "what": str, "stack": str, "claims": [str]}],
 "achievements": [str],
 "repo_facts": [{"path": str, "fact": str}],
 "probe_points": [str]}
- repo_facts: 6-10 concrete, checkable facts about the GitHub code, each tied to a real file path from the material
  (a library choice, an algorithm, how data flows, an error-handling gap, a hard-coded value, missing tests).
  Empty list if no repo material.
- probe_points: 4-6 things a sharp interviewer would want to verify or dig into (vague claims, big numbers, gaps)."""


async def build_dossier(track: str, fields: dict, resume_pdf: bytes | None, resume_text: str,
                        github_url: str, jd: str) -> dict:
    repo = None
    repo_error = None
    if github_url:
        try:
            repo = await fetch_repo(github_url)
        except (ContextError, httpx.HTTPError) as e:
            repo_error = str(e)

    material = [f"Interview track: {track}", f"Form fields: {fields}"]
    if resume_text:
        material.append(f"Resume text:\n{resume_text[:8000]}")
    if jd:
        material.append(f"Job description / target role:\n{jd[:4000]}")
    if repo:
        material.append(f"GitHub repo {repo['name']} ({repo['language']}): {repo['description']}")
        for path, text in repo["files"].items():
            material.append(f"--- FILE {path} ---\n{text}")
    parts = []
    if resume_pdf:
        parts.append({"inline_data": {"mime_type": "application/pdf", "data": base64.b64encode(resume_pdf).decode()}})
        material.append("The attached PDF is the candidate's resume.")

    if llm.available() and (resume_pdf or resume_text or repo or jd):
        d = await llm.ask_json(SYSTEM_DOSSIER, "\n\n".join(material), temperature=0.2, parts=parts)
    else:
        d = {"summary": "", "education": [], "experience": [], "skills": [], "projects": [],
             "achievements": [], "repo_facts": [], "probe_points": []}
    known = set(repo["files"]) if repo else set()
    d["repo_facts"] = [f for f in d.get("repo_facts", []) if f.get("path") in known]  # drop invented paths
    d["fields"] = {k: v for k, v in fields.items() if v}
    d["jd"] = jd[:1500]
    if repo:
        d["repo"] = {"name": repo["name"], "url": repo["url"], "files_read": list(repo["files"])}
    if repo_error:
        d["repo_error"] = repo_error
    return d
