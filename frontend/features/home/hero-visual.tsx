"use client";

import { Check, FileCode2, MessageCircle } from "lucide-react";
import { useEffect, useState } from "react";
import type { Dict } from "@/lib/i18n";
import { cn } from "@/lib/format";

const STEP_MS = 1700;
const LAST = 5;

/**
 * Illustrative phone (clearly labelled "sample") that plays an order from request to result:
 * the progress bar fills, the status chip changes, a message and the checked files appear.
 * It floats gently; with reduced motion it shows one still frame.
 */
export function HeroVisual({ t }: { t: Dict }) {
  const stages = t.stage;
  const [step, setStep] = useState(3);
  const [still, setStill] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setStill(true); setStep(4); return; }
    setStep(0);
    let s = 0;
    const id = setInterval(() => {
      s = s >= LAST + 2 ? 0 : s + 1; // hold the finished state for two beats, then replay
      setStep(Math.min(s, LAST));
    }, STEP_MS);
    return () => clearInterval(id);
  }, []);

  const statuses = t.home.mockStatuses;
  return (
    <div className="relative mx-auto w-full max-w-[340px] lg:mr-6" aria-hidden>
      <div className="absolute -inset-10 -z-10 rounded-full bg-[radial-gradient(closest-side,var(--glow),transparent)] opacity-80" />
      <div className={cn(!still && "animate-[vimora-float_7s_ease-in-out_infinite]")}>
        <div className="rotate-[4deg] rounded-[46px] bg-[#17201d] p-3 ring-1 ring-black/5 dark:bg-[#0f0d0b] dark:ring-white/10 shadow-[0_40px_80px_-30px_rgb(24_33_30/0.55)]">
          <div className="overflow-hidden rounded-[36px] bg-bg">
            <div className="flex items-center justify-between px-6 pb-3 pt-5 text-[11px] text-muted">
              <span className="font-[family-name:var(--font-display)] font-semibold tracking-[0.2em] text-ink">VIMORA</span>
              <span className="rounded-full bg-raised px-2 py-0.5">{t.home.mockSample}</span>
            </div>
            <div className="space-y-4 px-5 pb-6">
              <div className="rounded-[22px] bg-surface p-4 shadow-[var(--shadow-soft)]">
                <p className="eyebrow !text-[10px]">{t.home.mockOrder} · VM-2026-00125</p>
                <p className="mt-2 font-[family-name:var(--font-display)] text-[20px] leading-tight text-ink">{t.home.mockService}</p>
                <div className="mt-4 grid grid-cols-6 gap-1">
                  {stages.map((s, i) => (
                    <span key={s} className="h-1.5 overflow-hidden rounded-full bg-raised">
                      <span className={cn("block h-full rounded-full bg-accent transition-all duration-700 ease-out", i < step ? "w-full" : i === step ? "w-full opacity-45" : "w-0")} />
                    </span>
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between text-[12px]">
                  <span key={`st-${step}`} className="animate-[vimora-fade-up_.45s_ease-out] text-muted">{stages[step]}</span>
                  <span key={`ch-${step}`} className={cn("animate-[vimora-pop_.4s_ease-out] rounded-full px-2.5 py-0.5 font-medium",
                    step === LAST ? "bg-tint-1 text-ok" : "bg-tint-0 text-accent")}>{statuses[step]}</span>
                </div>
              </div>
              <div className={cn("flex items-start gap-2.5 transition-all duration-500 ease-out", step >= 3 ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0")}>
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-tint-1 text-ok"><MessageCircle className="h-4 w-4" /></span>
                <div className="rounded-[16px] rounded-tl-sm bg-surface px-3.5 py-2.5 text-[12.5px] leading-snug text-fg shadow-[var(--shadow-soft)]">
                  {step === 3 ? <TypingDots /> : t.home.steps[3]?.d}
                </div>
              </div>
              <div className={cn("flex items-center gap-3 rounded-[16px] border border-border bg-surface px-3.5 py-3 transition-all duration-500 ease-out", step >= 4 ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0")}>
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-tint-2 text-[#3d5a80] dark:text-[#9fb8d8]"><FileCode2 className="h-4 w-4" /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12.5px] font-medium text-ink">bot.py · README.md</p>
                  <p className="text-[11.5px] text-muted">{t.home.mockDone}</p>
                </div>
                <span className={cn("grid h-6 w-6 place-items-center rounded-full bg-ok text-white transition-transform duration-300", step >= 4 ? "scale-100" : "scale-0")}><Check className="h-3.5 w-3.5" /></span>
              </div>
              <div className={cn("rounded-full py-3 text-center text-[13px] font-semibold transition-colors duration-500",
                step === LAST ? "animate-[vimora-glow_1.6s_ease-in-out_infinite] bg-accent text-accent-fg" : "bg-accent/35 text-accent-fg/90")}>{t.home.mockCta}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="flex h-[1.1em] items-center gap-1 py-1">
      {[0, 1, 2].map((i) => <span key={i} className="h-1.5 w-1.5 animate-[vimora-dot_1s_ease-in-out_infinite] rounded-full bg-muted" style={{ animationDelay: `${i * 0.15}s` }} />)}
    </span>
  );
}
