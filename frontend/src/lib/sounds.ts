let audio: AudioContext | null = null;

function enabled() {
  return window.localStorage.getItem("circuitsage:sound") !== "0";
}

function context() {
  audio ??= new AudioContext();
  return audio;
}

function tone(freq: number, durationMs: number, type: OscillatorType = "sine") {
  if (!enabled() || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const ctx = context();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.0001, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.035, ctx.currentTime + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + durationMs / 1000);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + durationMs / 1000);
}

export function playTick() {
  tone(740, 55, "triangle");
}

export function playChime() {
  tone(523, 120);
  window.setTimeout(() => tone(784, 140), 90);
}
