// Mic recorder that produces 16 kHz mono WAV chunks (Gnani STT accepts WAV, max 60 s per request).
export class WavRecorder {
  constructor(chunkSeconds = 50) {
    this.chunkSeconds = chunkSeconds;
    this.targetRate = 16000;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    this.ctx = new AudioContext();
    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.node = this.ctx.createScriptProcessor(4096, 1, 1);
    this.samples = [];
    this.level = 0;
    this.node.onaudioprocess = (e) => {
      const d = e.inputBuffer.getChannelData(0);
      this.samples.push(new Float32Array(d));
      let sum = 0;
      for (let i = 0; i < d.length; i += 8) sum += d[i] * d[i];
      this.level = Math.min(1, Math.sqrt(sum / (d.length / 8)) * 6); // 0..1, drives the voice aura
    };
    this.source.connect(this.node);
    this.node.connect(this.ctx.destination);
    this.startedAt = performance.now();
  }

  seconds() {
    return this.startedAt ? (performance.now() - this.startedAt) / 1000 : 0;
  }

  async stop() {
    this.node.disconnect();
    this.source.disconnect();
    this.stream.getTracks().forEach((t) => t.stop());
    const rate = this.ctx.sampleRate;
    await this.ctx.close();
    const pcm = downsample(concat(this.samples), rate, this.targetRate);
    const per = this.chunkSeconds * this.targetRate;
    const chunks = [];
    for (let i = 0; i < pcm.length; i += per) chunks.push(encodeWav(pcm.subarray(i, i + per), this.targetRate));
    const secs = pcm.length / this.targetRate;
    this.startedAt = null;
    return { chunks, seconds: secs, whole: encodeWav(pcm, this.targetRate) };
  }
}

function concat(parts) {
  const out = new Float32Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

function downsample(buf, from, to) {
  if (from === to) return buf;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(buf.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const s = Math.floor(i * ratio), e = Math.min(Math.floor((i + 1) * ratio), buf.length);
    let sum = 0;
    for (let j = s; j < e; j++) sum += buf[j];
    out[i] = sum / Math.max(1, e - s);
  }
  return out;
}

function encodeWav(pcm, rate) {
  const buf = new ArrayBuffer(44 + pcm.length * 2);
  const v = new DataView(buf);
  const w = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVE");
  w(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}
