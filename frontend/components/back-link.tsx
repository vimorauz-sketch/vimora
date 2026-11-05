"use client";

import { ArrowLeft } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

// counts client-side page changes, so "back" knows the previous page is on this site
let inAppNavs = 0;

/** Mounted once in the root providers. */
export function NavTracker() {
  const path = usePathname();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    inAppNavs += 1;
  }, [path]);
  return null;
}

/** "Back" that returns to the exact previous page (search, filters, scroll) when it was on this site; otherwise opens `fallback`. */
export function BackLink({ fallback, label }: { fallback: string; label: string }) {
  const router = useRouter();
  return (
    <a href={fallback}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        const fromHere = inAppNavs > 0 || document.referrer.startsWith(window.location.origin);
        if (fromHere && window.history.length > 1) router.back();
        else router.push(fallback);
      }}
      className="group inline-flex items-center gap-2 rounded-full border border-border bg-surface py-1.5 pl-2 pr-4 text-[13.5px] font-medium shadow-[var(--shadow-soft)] transition-all hover:border-accent/50 hover:shadow-[var(--shadow-lift)]">
      <span className="grid h-7 w-7 place-items-center rounded-full bg-tint-0 text-accent transition-transform group-hover:-translate-x-0.5"><ArrowLeft className="h-4 w-4" aria-hidden /></span>
      {label}
    </a>
  );
}
