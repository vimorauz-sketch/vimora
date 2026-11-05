/**
 * VIMORA notification sounds, synthesized with the Web Audio API (no audio files to download).
 * Original short melodies; each event kind has its own tune, each style its own instrument.
 */

export type SoundStyle = "bells" | "marimba" | "harp";
export type SoundKind = "order" | "payment" | "message" | "alert" | "soft";

type Note = { f: number; t: number; d?: number; v?: number };

const N = (name: string): number => {
  const m = /^([A-G])(#?)(\d)$/.exec(name);
  if (!m) return 440;
  const idx = { C: -9, D: -7, E: -5, F: -4, G: -2, A: 0, B: 2 }[m[1] as "C"] + (m[2] ? 1 : 0) + (Number(m[3]) - 4) * 12;
  return 440 * 2 ** (idx / 12);
};
const seq = (notes: [string, number, number?, number?][]): Note[] => notes.map(([n, t, d, v]) => ({ f: N(n), t, d, v }));

/** Melodies (time in seconds). */
export const MELODIES: Record<SoundKind, Note[]> = {
  // bright rising arpeggio that resolves upward: "a new order arrived"
  order: seq([["G5", 0], ["B5", 0.11], ["D6", 0.22], ["G6", 0.33, 1.2], ["D6", 0.33, 1.2, 0.35], ["B6", 0.5, 1.4, 0.5]]),
  // joyful little fanfare with a sparkle on top: "money received"
  payment: seq([["C6", 0], ["E6", 0.09], ["G6", 0.18], ["C7", 0.3, 1.0], ["E6", 0.3, 1.0, 0.35], ["G6", 0.3, 1.0, 0.35], ["E7", 0.52, 0.5, 0.35], ["G7", 0.62, 0.9, 0.3]]),
  // two soft notes, like a gentle knock: "a new message"
  message: seq([["D6", 0, 0.7, 0.8], ["A6", 0.16, 1.1, 0.75]]),
  // calm descending figure that asks for attention without alarm
  alert: seq([["E6", 0, 0.5], ["C6", 0.18, 0.5], ["A5", 0.36, 1.2], ["E5", 0.36, 1.2, 0.35]]),
  // single quiet chime for background events
  soft: seq([["A6", 0, 0.9, 0.45]]),
};

export function kindFor(eventType: string): SoundKind | null {
  if (eventType === "ai.started") return null;
  if (eventType.startsWith("payment.final") || eventType === "payment.deposit_received") return "payment";
  if (eventType === "payment.failed" || eventType === "ai.failed" || eventType === "order.cancelled" || eventType === "review.required" || eventType === "revision.requested") return "alert";
  if (eventType === "order.deadline_soon") return "alert";
  if (eventType === "message.received" || eventType === "handover.proposed" || eventType === "file.received") return "message";
  if (eventType === "order.created" || eventType === "custom_request.created" || eventType === "quotation.accepted") return "order";
  return "soft";
}

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let reverb: ConvolverNode | null = null;

function context(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
    master = ctx.createGain();
    const comp = ctx.createDynamicsCompressor();
    master.connect(comp).connect(ctx.destination);
    // small hall: generated impulse response (decaying stereo noise)
    reverb = ctx.createConvolver();
    const len = Math.floor(ctx.sampleRate * 1.8);
    const ir = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = ir.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len) ** 3.2;
    }
    reverb.buffer = ir;
    const wet = ctx.createGain();
    wet.gain.value = 0.28;
    reverb.connect(wet).connect(master);
  }
  return ctx;
}

/** True once the browser allows sound (after the first click/keypress on the page). */
export function soundReady(): boolean {
  return !!ctx && ctx.state === "running";
}

export async function unlockSound(): Promise<boolean> {
  const c = context();
  if (!c) return false;
  if (c.state !== "running") await c.resume().catch(() => undefined);
  return c.state === "running";
}

function voice(c: AudioContext, out: AudioNode, style: SoundStyle, f: number, at: number, dur: number, vel: number) {
  const env = c.createGain();
  env.connect(out);
  const partials: [number, number, OscillatorType][] =
    style === "bells" ? [[1, 1, "sine"], [2.76, 0.32, "sine"], [5.4, 0.12, "sine"], [2, 0.18, "sine"]]
      : style === "marimba" ? [[1, 1, "sine"], [3.9, 0.22, "sine"], [10, 0.05, "sine"]]
        : [[1, 1, "triangle"], [2, 0.3, "sine"], [3, 0.12, "sine"]];
  const attack = style === "harp" ? 0.004 : 0.006;
  const length = style === "marimba" ? Math.min(dur, 0.6) : dur;
  env.gain.setValueAtTime(0.0001, at);
  env.gain.exponentialRampToValueAtTime(vel, at + attack);
  env.gain.exponentialRampToValueAtTime(0.0001, at + length);
  let target: AudioNode = env;
  if (style === "harp") {
    const lp = c.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(f * 8, at);
    lp.frequency.exponentialRampToValueAtTime(f * 1.5, at + length);
    lp.connect(env);
    target = lp;
  }
  for (const [mult, amp, type] of partials) {
    const o = c.createOscillator();
    const g = c.createGain();
    o.type = type;
    o.frequency.value = f * mult;
    g.gain.value = amp;
    if (mult > 2) { // upper partials die faster: gives the "struck" sound
      g.gain.setValueAtTime(amp, at);
      g.gain.exponentialRampToValueAtTime(0.0001, at + length * 0.35);
    }
    o.connect(g).connect(target);
    o.start(at);
    o.stop(at + length + 0.05);
  }
}

export function playSound(kind: SoundKind, style: SoundStyle = "bells", volume = 0.7): boolean {
  const c = context();
  if (!c || !master || !reverb) return false;
  if (c.state !== "running") { void c.resume(); return false; }
  master.gain.value = Math.max(0, Math.min(1, volume)) * 0.9;
  const dry = c.createGain();
  dry.gain.value = 1;
  dry.connect(master);
  dry.connect(reverb);
  const start = c.currentTime + 0.03;
  for (const n of MELODIES[kind]) voice(c, dry, style, n.f, start + n.t, n.d ?? 0.7, (n.v ?? 1) * 0.22);
  return true;
}
