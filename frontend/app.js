import { WavRecorder } from "./recorder.js";
import { InterviewCamera } from "./camera.js";

const cam = new InterviewCamera();

const $ = (id) => document.getElementById(id);
const ORDER = ["step-track", "step-intake", "step-dossier", "room", "report"];
let current = "step-track";
const show = (id, push = true) => {
  if (push && id !== current) history.pushState({ id }, "");
  current = id;
  if (id === "room") hasReport = false;            // a new interview replaces the old report
  if (id === "report") hasReport = true;
  ORDER.forEach((s) => ($(s).hidden = s !== id));
  document.body.classList.toggle("in-room", id === "room");
  paintSteps();
  window.scrollTo({ top: 0 });
};
let hasReport = false;
// A step is clickable whenever its data exists, not only when it lies behind the current step.
const canOpen = (s) => s === "step-track" || (s === "step-intake" && !!TRACK)
  || (s === "step-dossier" && !!S?.dossier) || (s === "report" && hasReport);
function paintSteps() {
  const at = ORDER.indexOf(current);
  document.querySelectorAll("#steps i").forEach((el) => {
    const s = el.dataset.s, i = ORDER.indexOf(s);
    el.className = s === current ? "on" : [i < at ? "done" : "", s !== "room" && canOpen(s) ? "go" : ""].join(" ").trim();
  });
}
const initials = (t) => t.replace(/\(.*?\)/g, "").split(/\s+/).filter(Boolean).map((w) => (/\d/.test(w) ? w : w[0])).join("").slice(0, 2).toUpperCase();
const FIELD_DEFS = {
  home: ["Home state and district", "e.g. Bihar, Muzaffarpur"],
  graduation: ["Graduation (degree, college)", "e.g. B.Tech ECE, NSUT"],
  optional: ["Optional subject", "e.g. Sociology"],
  hobbies: ["Hobbies", "e.g. chess, Hindi poetry"],
  role: ["Target role / company", "e.g. SDE intern, Big 4 audit, sales executive"],
  ca_level: ["CA level", "Foundation / Inter / Final / Qualified"],
  other: ["Anything else", "work, internships, NCC, sports, achievements"],
};
const LANG_NAMES = { hi: "हिन्दी (Hindi)", en: "English" };
const CLONE_SCRIPT = {
  hi: "मेरी तैयारी अपने लक्ष्य के लिए चल रही है। मुझे लगता है कि किसी भी काम का असली मतलब सामने वाले की समस्या को ध्यान से सुनना और समय पर हल करना है। अपने उत्तरों को और स्पष्ट और संतुलित बनाना मेरा लक्ष्य है।",
  en: "I am preparing seriously for this interview. I believe good work starts with listening carefully to the problem and solving it on time. Today my goal is to make my answers clearer, more specific and more balanced.",
};
const LABELS = { intro: "Introduction", why: "Motivation", resume: "Resume", project: "Project deep-dive", repo_file: "Your code",
  fundamentals: "Fundamentals", dsa: "Problem solving", scenario: "Scenario", behavioral: "Behavioural", current: "Current affairs",
  case: "Case", home: "Home state", hobby: "Hobbies", closing: "Closing" };

let CFG, TRACK, S, pending, rec, tick, busy = false, demoMode = false;
// Hands-free answering: the mic opens after each question.
const WAIT_TO_START = 20;   // seconds of silence before the panel moves on
const END_PAUSE = 3;        // seconds of silence that end an answer
let gen = 0;                // bumped when the candidate leaves the room; stale async work checks it
let micDenied = false, curAudio = null;
const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
const strip = (t) => t.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// One colour tile + line icon per track (paths in the style of Lucide icons).
const TRACK_ICONS = {
  upsc: ["indigo", '<path d="M3 21h18M5 21V10M19 21V10M9 21v-7M15 21v-7M2 10l10-6 10 6"/>'],
  software: ["blue", '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>'],
  core: ["teal", '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M10 2v3M14 2v3M10 19v3M14 19v3M2 10h3M2 14h3M19 10h3M19 14h3"/>'],
  ca: ["amber", '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M8 6h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01M8 19h8"/>'],
  mba: ["rose", '<path d="M22 10 12 5 2 10l10 5 10-5Z"/><path d="M6 12v5c3 2 9 2 12 0v-5"/>'],
  bank: ["green", '<path d="M6 3h12M6 8h12M14.5 21 6 13h3c6.67 0 6.67-10 0-10"/>'],
  consulting: ["violet", '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>'],
  custom: ["slate", '<path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z"/><path d="M9 13h6M9 17h4"/>'],
};

async function init() {
  CFG = await (await fetch("/api/status")).json();
  $("status").textContent = `Gnani voices ${CFG.gnani ? "on" : "off: browser voice and typing"} · Panel ${CFG.llm ? "live" : "offline: fixed questions"}`;
  $("tracks").innerHTML = Object.entries(CFG.tracks).map(([k, t]) => {
    const [tone, path] = TRACK_ICONS[k] || TRACK_ICONS.custom;
    return `<button class="track" data-k="${k}">
      <span class="t-icon t-${tone}" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${path}</svg></span>
      <span class="name">${esc(t.name)}</span><span class="tag">${esc(t.tag)}</span>
      <span class="panel"><span class="stack sm" aria-hidden="true">${t.panel.map((_, j) => `<img src="/static/avatars/p${(j % 7) + 1}.svg" alt="" />`).join("")}</span><span><b>${t.panel.length} panelists</b> · ${t.panel.map((m) => esc(m.title)).join(", ")}</span></span>
      <span class="arrow" aria-hidden="true">Start →</span></button>`;
  }).join("");
  document.querySelectorAll(".track").forEach((b) => (b.onclick = () => pickTrack(b.dataset.k)));
}

function pickTrack(k) {
  TRACK = k;
  const t = CFG.tracks[k];
  $("intakeTrack").textContent = t.name;
  $("trackFields").innerHTML = t.fields.filter((f) => f !== "github").map((f) =>
    `<label class="field"><span class="lbl">${FIELD_DEFS[f][0]}</span><input name="f_${f}" placeholder="${esc(FIELD_DEFS[f][1])}" /></label>`).join("");
  $("ghWrap").hidden = !t.fields.includes("github");
  $("langSel").innerHTML = t.langs.map((l) => `<option value="${l}">${LANG_NAMES[l]}</option>`).join("");
  $("planSel").innerHTML = Object.entries(t.lengths).map(([p, n]) => `<option value="${p}">${p === "short" ? "Quick" : "Full"} (${n} questions)</option>`).join("");
  show("step-intake");
}

$("intake").onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const fields = {};
  for (const [k, v] of fd.entries()) if (k.startsWith("f_") && v) fields[k.slice(2)] = v;
  S = { track: TRACK, lang: fd.get("lang"), plan: fd.get("plan"), pressure: fd.get("pressure"),
        browserVoice: !!fd.get("browserVoice"), dossier: {}, history: [] };
  const body = new FormData();
  body.append("track", TRACK);
  body.append("fields", JSON.stringify(fields));
  body.append("resume_text", fd.get("resume_text") || "");
  body.append("github_url", fd.get("github_url") || "");
  body.append("jd", fd.get("jd") || "");
  const file = fd.get("resume");
  if (file && file.size) body.append("resume", file);
  $("prepBtn").disabled = true;
  $("prepBtn").textContent = "Reading your file…";
  try {
    const r = await fetch("/api/intake", { method: "POST", body });
    if (!r.ok) throw new Error(await r.text());
    S.dossier = await r.json();
    renderDossier(S.dossier);
    show("step-dossier");
  } catch (err) {
    alert("Could not brief the panel: " + err.message);
  } finally {
    $("prepBtn").disabled = false;
    $("prepBtn").textContent = "Brief the panel";
  }
};

function list(title, items, fmt = (x) => esc(x)) {
  return items && items.length ? `<h4>${title}</h4><ul>${items.map((x) => `<li>${fmt(x)}</li>`).join("")}</ul>` : "";
}

function renderDossier(d) {
  const f = Object.entries(d.fields || {}).map(([k, v]) => `<li><b>${esc(FIELD_DEFS[k]?.[0] || k)}:</b> ${esc(v)}</li>`).join("");
  $("dossier").innerHTML =
    (d.summary ? `<p class="summary">${esc(d.summary)}</p>` : "") +
    (f ? `<ul>${f}</ul>` : "") +
    list("Projects", d.projects, (p) => `<b>${esc(p.name)}</b>: ${esc(p.what)} <span class="muted">${esc(p.stack)}</span>`) +
    list("Experience", d.experience) + (d.skills?.length ? `<h4>Skills</h4><div class="chips">${d.skills.map((x) => `<span>${esc(x)}</span>`).join("")}</div>` : "") +
    (d.repo ? `<h4>GitHub: <a href="${esc(d.repo.url)}" target="_blank" rel="noopener">${esc(d.repo.name)}</a></h4><p class="muted">Files read: ${d.repo.files_read.map(esc).join(", ")}</p>` : "") +
    list("Code facts the panel may ask about", d.repo_facts, (x) => `<code>${esc(x.path)}</code> ${esc(x.fact)}`) +
    (d.repo_error ? `<p class="warn">GitHub: ${esc(d.repo_error)}</p>` : "") +
    list("What the panel wants to dig into", d.probe_points) ||
    "<p>No resume or links given. The panel will ask general questions for this track.</p>";
}

function renderBoard() {
  $("board").innerHTML = CFG.tracks[S.track].panel.map((m, i) =>
    `<div class="seat" id="mem-${m.id}"><div class="avatar" aria-hidden="true"><img src="/static/avatars/p${(i % 7) + 1}.svg" alt="" /></div><div class="plate">${esc(m.title)}</div></div>`).join("");
}
const memberOf = (id) => CFG.tracks[S.track].panel.find((m) => m.id === id);
const highlight = (id) => document.querySelectorAll(".seat").forEach((el) => el.classList.toggle("speaking", el.id === `mem-${id}`));

// Live voice level -> CSS --lvl, so the aura around the speaker follows the real audio.
let actx, analyser, levelBuf;
function setLevel(v) { document.documentElement.style.setProperty("--lvl", v.toFixed(3)); }
function meter(audio) {
  try {
    actx = actx || new AudioContext();
    if (actx.state === "suspended") actx.resume();
    const src = actx.createMediaElementSource(audio);
    analyser = analyser || Object.assign(actx.createAnalyser(), { fftSize: 512 });
    levelBuf = levelBuf || new Uint8Array(analyser.fftSize);
    src.connect(analyser);
    if (!analyser._wired) { analyser.connect(actx.destination); analyser._wired = true; }
    const loop = () => {
      if (audio.ended || audio.paused) return setLevel(0);
      analyser.getByteTimeDomainData(levelBuf);
      let sum = 0;
      for (const b of levelBuf) sum += (b - 128) ** 2;
      setLevel(Math.min(1, Math.sqrt(sum / levelBuf.length) / 40));
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  } catch { /* metering is decoration only */ }
}

async function speak(text, speaker) {
  highlight(speaker);
  try {
    if (S.browserVoice) throw new Error("browser voice chosen");
    const r = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice: memberOf(speaker).voice, lang: S.lang }) });
    if (!r.ok) throw new Error(await r.text());
    await playBlob(await r.blob());
  } catch (e) {
    if (!S.browserVoice) console.warn("Gnani voice unavailable, using browser voice:", e.message);
    await browserSpeak(sayPaths(strip(text)));
  }
  highlight(null);
}

function playBlob(blob) { return playUrl(URL.createObjectURL(blob)); }
function playUrl(url) {
  return new Promise((res) => {
    const a = new Audio(url);
    curAudio = a;
    a._done = res;
    a.onended = a.onerror = () => { setLevel(0); res(); };
    meter(a);
    a.play().catch(res);
  });
}
// Same idea as backend board.spoken(): read "api/index.js" as words, not "slash".
function sayPaths(t) {
  return t.replace(/https?:\/\/\S+/g, "the link")
    .replace(/(?<![\w\/.-])\/?[\w.-]*[A-Za-z][\w.-]*(?:\/[\w.-]*)*/g, (p) => {
      if (!p.includes("/")) return p;
      const tail = p.match(/\.*$/)[0]; p = p.slice(0, p.length - tail.length);
      if (/^[a-z]+\/[a-z]+$/i.test(p) && !/\.\w+$/.test(p)) return p; // and/or
      const parts = p.split("/").filter(Boolean);
      const f = parts.pop().replace(/\.(\w+)$/, " dot $1");
      return (parts.length ? `${f} in the ${parts.pop()} folder` : `the ${f} folder`) + tail;
    });
}
function browserSpeak(text) {
  return new Promise((res) => {
    if (!("speechSynthesis" in window)) return res();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = S.lang === "hi" ? "hi-IN" : "en-IN";
    const guard = setTimeout(res, 2000 + text.split(/\s+/).length * 600); // some browsers never fire onend
    u.onend = u.onerror = () => { clearTimeout(guard); res(); };
    speechSynthesis.speak(u);
  });
}

async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

function ensureAudio() {
  actx = actx || new AudioContext();
  analyser = analyser || Object.assign(actx.createAnalyser(), { fftSize: 512 });
  if (actx.state === "suspended") actx.resume();
}

function stopVoices() {
  try { speechSynthesis.cancel(); } catch {}
  if (curAudio) { curAudio.pause(); curAudio._done?.(); curAudio = null; }
  setLevel(0);
}

// Leave the room cleanly: stop voices, mic, camera and any in-flight turn.
async function leaveRoom() {
  gen++;
  clearInterval(tick);
  stopVoices();
  if (rec) { const r = rec; rec = null; await r.cancel(); }
  if (cam.recorder) await cam.stop();
  else cam.disable($("camPreview"));
  $("camToggle").checked = false; $("camPreview").hidden = true; $("camMsg").textContent = "";
  $("recDot").hidden = true;
  $("micBtn").classList.remove("rec");
  $("room").classList.remove("demo");
  highlight(null);
  busy = false; pending = null;
  const wasDemo = demoMode; demoMode = false;
  return wasDemo ? "step-track" : "step-dossier";
}

function startInterview() {
  gen++;
  S.history = []; S.report = null; pending = null; busy = false;
  $("typeBox").open = false; $("typed").value = ""; $("you").textContent = ""; $("timer").textContent = "0:00";
  if (cam.on) {
    ensureAudio();
    cam.start(actx, analyser);
    $("camPreview").hidden = true;
    $("recDot").hidden = false;
  }
  $("limit").textContent = CFG.pressure[S.pressure];
  if (!CFG.gnani) $("typeBox").open = true;
  show("room");
  renderBoard();
  nextTurn();
}

async function nextTurn() {
  const g = gen;
  busy = true;
  $("micBtn").disabled = true;
  $("question").textContent = "…";
  let data;
  try {
    data = await post("/api/turn", S);
    if (g !== gen) return;
  } catch (e) {
    if (g !== gen) return;
    $("question").textContent = "The panel could not respond (" + e.message + "). Click the button to retry.";
    busy = false; $("micBtn").disabled = false;
    return;
  }
  if (data.reaction) {
    $("speaker").textContent = memberOf(data.reaction.speaker).title;
    $("question").textContent = strip(data.reaction.text);
    await speak(data.reaction.text, data.reaction.speaker);
    if (g !== gen) return;
  }
  const n = data.next;
  if (n.done) return finish();
  pending = { speaker: n.speaker, question: strip(n.text) };
  cam.mark(`Q${n.index + 1} · ${LABELS[n.qtype] || ""}`);
  $("progress").textContent = `${n.index + 1} / ${n.total} · ${LABELS[n.qtype] || ""}`;
  $("progressFill").style.width = `${((n.index + 1) / n.total) * 100}%`;
  $("speaker").textContent = n.title;
  $("question").textContent = strip(n.text);
  $("you").textContent = "";
  await speak(n.text, n.speaker);
  if (g !== gen) return;
  if (n.closing) { S.history.push({ ...pending, answer: "", seconds: 0 }); return finish(); }
  busy = false;
  $("micBtn").disabled = false;
  if (!micDenied && !$("typed").value.trim()) startAnswer();
}

async function startAnswer() {
  if (busy || rec || !pending) return;
  const g = gen;
  try { rec = new WavRecorder(); await rec.start(); } catch {
    rec = null; micDenied = true;
    $("you").textContent = "Microphone not available. Type your answer below."; $("typeBox").open = true; return;
  }
  if (g !== gen) { const r = rec; rec = null; return r.cancel(); }
  $("micBtn").classList.add("rec");
  let waitFrom = performance.now();
  tick = setInterval(() => {
    if (!rec) return;
    setLevel(rec.level || 0);
    const spoke = rec.speakingSeconds();
    $("timer").textContent = clock(Math.floor(spoke));
    if (!rec.heard) {
      if (document.activeElement === $("typed")) waitFrom = performance.now(); // typing: do not move on
      const left = Math.max(0, Math.ceil(WAIT_TO_START - (performance.now() - waitFrom) / 1000));
      $("micLabel").textContent = `Listening… start speaking when ready (${left}s)`;
      if (left <= 0) stopAnswer();
      return;
    }
    const pause = rec.silentFor();
    $("micLabel").textContent = pause >= 1.2
      ? `Paused… finishing in ${Math.max(1, Math.ceil(END_PAUSE - pause))}s (keep talking to continue)`
      : "Listening… pause or tap the mic when you finish";
    if (pause >= END_PAUSE || spoke >= CFG.pressure[S.pressure]) stopAnswer();
  }, 200);
}

async function stopAnswer() {
  if (!rec) return;
  clearInterval(tick);
  const g = gen;
  const r = rec; rec = null; busy = true;
  $("micBtn").classList.remove("rec");
  setLevel(0);
  $("micLabel").textContent = "The mic opens by itself after each question";
  $("micBtn").disabled = true;
  const { chunks, seconds } = await r.stop();
  if (g !== gen) return;
  if (!chunks.length) return submitAnswer("", 0);
  $("you").textContent = "Listening to your answer…";
  const parts = [];
  for (const [i, c] of chunks.entries()) {
    const fd = new FormData();
    fd.append("audio", c, "answer.wav");
    fd.append("lang", S.lang);
    fd.append("seconds", String(Math.min(50, seconds - i * 50)));
    const resp = await fetch("/api/stt", { method: "POST", body: fd });
    if (g !== gen) return;
    if (resp.ok) { parts.push((await resp.json()).transcript); continue; }
    $("you").textContent = resp.status === 429 ? "Today's free listening budget is used up. Please type your answer." : "Could not hear that. Please type your answer.";
    $("typeBox").open = true; busy = false; $("micBtn").disabled = false;
    return;
  }
  submitAnswer(parts.join(" ").trim(), seconds);
}

function submitAnswer(text, seconds) {
  $("you").textContent = text ? `You said: ${text}` : "No answer heard. The panel moves on.";
  S.history.push({ ...pending, answer: text, seconds });
  pending = null;
  $("timer").textContent = "0:00";
  nextTurn();
}

async function finish() {
  const g = gen;
  highlight(null);
  $("recDot").hidden = true;
  const video = await cam.stop();
  show("report");
  showReplay(video);
  $("cloneScript").textContent = CLONE_SCRIPT[S.lang];
  $("reportBody").innerHTML = "<p>The panel is discussing your interview…</p>";
  try { const R = await post("/api/report", S); if (g !== gen) return; S.report = R; renderReport(R); }
  catch (e) { if (g === gen) $("reportBody").textContent = "Feedback failed: " + e.message; }
}

function renderReport(R) {
  const bar = (k, v) => `<div class="bar"><span>${esc(k.replace(/_/g, " "))}</span><b>${esc(v)}</b><div class="track-line"><i style="width:${Math.max(0, Math.min(10, v)) * 10}%"></i></div></div>`;
  const D = R.delivery || {};
  const fillers = Object.entries(D.filler_words || {}).map(([w, n]) => `${esc(w)} ×${n}`).join(", ") || "none detected";
  const qs = (R.answers || []).map((a) => {
    const h = S.history[a.q - 1] || {};
    return `<div class="qa"><p class="q"><b>Q${a.q}</b>${esc(h.question)}</p>
      <p class="a"><i>You said</i>${esc(h.answer || "nothing recorded")}</p>
      <p class="v"><span>Verdict.</span> ${esc(a.verdict)}</p>
      ${a.missing ? `<p class="v"><span>Missing.</span> ${esc(a.missing)}</p>` : ""}
      ${a.better ? `<p class="better"><span>Your own points, better structured</span>${esc(a.better)}</p>` : ""}</div>`;
  }).join("");
  const block = (t, items) => (items && items.length ? `<div class="report-block"><h4>${t}</h4><ol>${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>` : "");
  $("reportBody").innerHTML = `
    <div class="score-hero"><div class="big">${esc(R.overall)}<small>/10</small></div><p>${esc(R.summary)}</p></div>
    <div class="cols"><div>${Object.entries(R.scores || {}).map(([k, v]) => bar(k, v)).join("")}</div>
      <div class="delivery"><h4>How you spoke</h4>
        <div class="stat"><span>Pace</span><b>${D.words_per_minute ?? "–"} words/min</b></div>
        <div class="stat"><span>Average answer</span><b>${D.avg_answer_seconds ?? 0} s</b></div>
        <div class="stat"><span>Longest answer</span><b>${D.longest_answer_seconds ?? 0} s</b></div>
        <div class="stat"><span>Filler words</span><b>${fillers}</b></div>
        <p class="muted">Counted by fixed rules from the transcript, so approximate.</p></div></div>
    ${block("Fix these first", R.top_tips)}
    ${block("Prepare these before the real interview", R.prepare_next)}
    <div class="report-block"><h4>Question by question</h4>${qs}</div>`;
  $("clone").hidden = !CFG.gnani || !(R.answers || []).some((a) => a.better);
}

function showReplay(v) {
  $("replay").hidden = !v;
  if (!v) return;
  const el = $("replayVideo");
  el.src = v.url;
  $("replayDownload").href = v.url;
  $("replayDownload").download = `board-room-interview.${v.type.includes("mp4") ? "mp4" : "webm"}`;
  $("chapters").innerHTML = v.marks.map((m, i) =>
    `<button class="chip-btn" data-i="${i}"><b>${esc(m.label.split(" · ")[0])}</b> ${esc(m.label.split(" · ")[1] || "")} <span>${clock(Math.floor(m.t))}</span></button>`).join("");
  $("chapters").querySelectorAll("button").forEach((b) => (b.onclick = () => {
    el.currentTime = v.marks[b.dataset.i].t;
    el.play().catch(() => {});
  }));
}

async function cloneFlow() {
  const btn = $("cloneRec");
  btn.disabled = true;
  const r = new WavRecorder(30);
  try { await r.start(); } catch { $("cloneOut").textContent = "Microphone not available."; return; }
  for (let s = 20; s > 0; s--) { btn.textContent = `Recording… ${s}s`; await new Promise((x) => setTimeout(x, 1000)); }
  const { whole } = await r.stop();
  btn.textContent = "Making your voice…";
  const fd = new FormData();
  fd.append("audio", whole, "voice.wav");
  const er = await fetch("/api/clone/embed", { method: "POST", body: fd });
  if (!er.ok) { $("cloneOut").textContent = "Voice clone failed: " + (await er.text()); btn.textContent = "Record 20 s"; btn.disabled = false; return; }
  const { embedding } = await er.json();
  btn.textContent = "Ready";
  const answers = (S.report?.answers || []).filter((a) => a.better);
  $("cloneOut").innerHTML = answers.map((a, i) =>
    `<p><button data-i="${i}">▶ Q${a.q}</button><span class="ai-label">AI voice</span> ${esc(a.better)}</p>`).join("");
  $("cloneOut").querySelectorAll("button").forEach((b) => (b.onclick = async () => {
    b.disabled = true;
    for (const s of answers[b.dataset.i].better.match(/[^.!?।]+[.!?।]?/g) || []) {
      if (!s.trim()) continue;
      const r2 = await fetch("/api/clone/speak", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: s.trim(), embedding, lang: S.lang }) });
      if (r2.ok) await playBlob(await r2.blob());
    }
    b.disabled = false;
  }));
}

// Zero-credit demo: pre-recorded Gnani audio, played with captions.
async function runDemo(which = "") {
  const base = `/static/demo/${which ? which + "/" : ""}`;
  const demo = await (await fetch(base + "demo.json")).json();
  const cloned = document.querySelector("input[name=demoVoice]:checked")?.value === "clone";
  demoMode = true;
  const g = ++gen;
  S = { track: demo.track, lang: demo.lang, history: [] };
  show("room");
  $("room").classList.add("demo");
  renderBoard();
  $("micBtn").disabled = true;
  $("progress").textContent = "Demo · recorded with Gnani voices";
  $("progressFill").style.width = "0%";
  for (const [i, step] of demo.steps.entries()) {
    $("progressFill").style.width = `${((i + 1) / demo.steps.length) * 100}%`;
    const who = step.speaker === "candidate" ? null : step.speaker;
    $("speaker").textContent = who ? memberOf(who).title : (cloned && step.audio_clone ? demo.candidate_label : "Candidate");
    $("question").textContent = step.caption;
    $("you").textContent = step.speaker === "candidate" ? "Candidate is answering…" : "";
    highlight(who);
    await playUrl(`/static/demo/${cloned && step.audio_clone ? step.audio_clone : step.audio}`);
    if (g !== gen) return;
    highlight(null);
    await new Promise((x) => setTimeout(x, 350));
    if (g !== gen) return;
  }
  S.history = demo.history;
  $("room").classList.remove("demo");
  show("report");
  renderReport(demo.report);
  $("clone").hidden = true;
}

$("back1").onclick = () => show("step-track");
$("back2").onclick = () => { cam.disable($("camPreview")); $("camToggle").checked = false; $("camPreview").hidden = true; show("step-intake"); };
$("camToggle").onchange = async (e) => {
  if (e.target.checked) {
    try {
      await cam.enable($("camPreview"));
      $("camPreview").hidden = false;
      $("camMsg").textContent = "Camera on. Frame your face and shoulders, with light in front of you.";
    } catch {
      e.target.checked = false;
      $("camMsg").textContent = "Camera not available or permission denied. You can still do the interview without it.";
    }
  } else {
    cam.disable($("camPreview"));
    $("camPreview").hidden = true;
    $("camMsg").textContent = "";
  }
};
$("startBtn").onclick = startInterview;
document.querySelectorAll(".demo-btn").forEach((b) => (b.onclick = () => runDemo(b.dataset.demo)));
$("endBtn").onclick = async () => {
  if (busy && !rec) return;
  if (rec) { clearInterval(tick); const r = rec; rec = null; await r.cancel(); $("micBtn").classList.remove("rec"); }
  finish();
};
$("micBtn").onclick = () => (rec ? stopAnswer() : (pending ? startAnswer() : nextTurn()));
async function dropMic() {
  if (!rec) return;
  clearInterval(tick);
  const r = rec; rec = null;
  $("micBtn").classList.remove("rec"); setLevel(0);
  $("micLabel").textContent = "Typing instead. Tap the mic to speak again.";
  await r.cancel();
}
$("typed").addEventListener("input", dropMic);
$("sendTyped").onclick = async () => {
  const t = $("typed").value.trim();
  if (!t || !pending || (busy && !rec)) return;
  await dropMic();
  $("typed").value = "";
  submitAnswer(t, Math.min(CFG.pressure[S.pressure] - 1, t.split(/\s+/).length / 2.2));
};
const inRoom = () => !$("room").hidden && !demoMode && document.activeElement.tagName !== "TEXTAREA";
// Space = "I am done" while listening, or "start listening" if the mic is off.
document.addEventListener("keydown", (e) => {
  if (e.code !== "Space" || e.repeat || !inRoom()) return;
  e.preventDefault();
  rec ? stopAnswer() : startAnswer();
});

// ---------- going back ----------
const LEAVE_MSG = "Leave this interview? Your answers so far will not be scored.";
let leaving = false;
$("backRoom").onclick = async () => {
  if (!demoMode && S.history.length && !confirm(LEAVE_MSG)) return;
  leaving = true;
  const to = await leaveRoom();
  if (history.state?.id === "room") history.back();   // pop the room entry, so browser Back keeps working
  else { leaving = false; show(to); }
};
$("backReport").onclick = () => { stopVoices(); show(S.dossier ? "step-dossier" : "step-track"); };
$("steps").addEventListener("click", async (e) => {
  const id = e.target.dataset?.s;
  if (!id || id === "room" || id === current || !canOpen(id)) return;
  if (current === "room") {
    if (!demoMode && S.history.length && !confirm(LEAVE_MSG)) return;
    await leaveRoom();
  }
  stopVoices();
  show(id);
});
history.replaceState({ id: "step-track" }, "");
window.addEventListener("popstate", async (e) => {
  let id = e.state?.id || "step-track";
  if (id === "room") id = "step-dossier";           // never re-enter a finished or abandoned room
  if (id === "step-dossier" && !S?.dossier) id = "step-track";
  if (current === "room" && !leaving) {
    if (!demoMode && S.history.length && !confirm(LEAVE_MSG)) { history.pushState({ id: "room" }, ""); return; }
    await leaveRoom();
  }
  leaving = false;
  stopVoices();
  show(id, false);
});
$("consent").onchange = (e) => ($("cloneRec").disabled = !e.target.checked);
$("cloneRec").onclick = cloneFlow;
$("again").onclick = () => location.reload();

init();

$("resumeIn").onchange = (e) => {
  const f = e.target.files[0];
  $("dropText").textContent = f ? `✓ ${f.name}` : "Drop your PDF here, or browse";
  e.target.closest(".drop").classList.toggle("has", !!f);
};
