// Records the whole interview (camera + your voice + the panel's voices) inside the browser.
// Nothing is uploaded: the video lives in memory as a Blob until the page closes or you download it.
const MAX_MINUTES = 20;

export class InterviewCamera {
  constructor() {
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.marks = [];
    this.startedAt = 0;
    this.mix = null;
  }

  get on() { return !!this.stream; }

  async enable(previewEl) {
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: { echoCancellation: true, noiseSuppression: true },
    });
    previewEl.srcObject = this.stream;
    previewEl.muted = true;
    await previewEl.play().catch(() => {});
  }

  disable(previewEl) {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    if (previewEl) previewEl.srcObject = null;
  }

  // ctx: the page AudioContext; panelNode: the node the panel's voices pass through.
  start(ctx, panelNode) {
    if (!this.stream) return;
    this.mix = ctx.createMediaStreamDestination();
    ctx.createMediaStreamSource(this.stream).connect(this.mix);
    panelNode?.connect(this.mix);
    const tracks = [...this.stream.getVideoTracks(), ...this.mix.stream.getAudioTracks()];
    const type = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"]
      .find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || "";
    this.recorder = new MediaRecorder(new MediaStream(tracks), { mimeType: type, videoBitsPerSecond: 1_000_000 });
    this.chunks = [];
    this.marks = [];
    this.recorder.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.recorder.start(1000);
    this.startedAt = performance.now();
    this.limit = setTimeout(() => this.recorder?.state === "recording" && this.recorder.stop(), MAX_MINUTES * 60000);
  }

  mark(label) {
    if (this.recorder?.state === "recording") this.marks.push({ label, t: (performance.now() - this.startedAt) / 1000 });
  }

  // Returns {url, type, marks, sizeMB} or null.
  async stop() {
    clearTimeout(this.limit);
    const r = this.recorder;
    if (!r) return null;
    if (r.state !== "inactive") await new Promise((res) => { r.onstop = res; r.stop(); });
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.recorder = null;
    if (!this.chunks.length) return null;
    const blob = new Blob(this.chunks, { type: r.mimeType || "video/webm" });
    this.chunks = [];
    return { url: URL.createObjectURL(blob), type: blob.type, marks: this.marks, sizeMB: blob.size / 1e6 };
  }
}
