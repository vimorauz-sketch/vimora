"use client";

import { useEffect, useState } from "react";

/**
 * Types the hero headline letter by letter. The full sentence is always in the DOM for
 * screen readers and search engines, and an invisible copy keeps the layout from jumping.
 * People who prefer reduced motion see the finished text at once.
 */
export function TypewriterHeadline({ a, em, b, className }: { a: string; em: string; b: string; className?: string }) {
  const parts = [a + " ", em, " " + b];
  const total = parts.join("").length;
  const [n, setN] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setN(total); setDone(true); return; }
    let i = 0;
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      i += 1;
      setN(i);
      if (i >= total) { timer = setTimeout(() => setDone(true), 2600); return; }
      const ch = parts.join("")[i - 1];
      timer = setTimeout(tick, ch === " " ? 95 : ch === "." ? 260 : 48 + Math.random() * 42);
    };
    timer = setTimeout(tick, 450);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [total]);

  let left = n;
  const typed = parts.map((p) => { const s = p.slice(0, Math.max(0, left)); left -= p.length; return s; });
  return (
    <h1 className={className}>
      <span className="sr-only">{a} {em} {b}</span>
      <span aria-hidden className="grid">
        {/* invisible full text reserves the final size (no layout shift) */}
        <span className="vimora-typed-fallback invisible col-start-1 row-start-1">{a} <em>{em}</em> {b}</span>
        <span className="col-start-1 row-start-1">
          {typed[0]}{typed[1] && <em>{typed[1]}</em>}{typed[2]}
          <span className={`ml-[0.04em] inline-block h-[0.82em] w-[0.06em] translate-y-[0.08em] rounded-full bg-accent align-baseline ${done ? "animate-[vimora-caret-out_.6s_ease_forwards]" : "animate-[vimora-caret_1s_steps(1)_infinite]"}`} />
        </span>
      </span>
      <noscript><style>{".vimora-typed-fallback{visibility:visible!important}"}</style></noscript>
    </h1>
  );
}
