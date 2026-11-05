import Link from "next/link";

/** VIMORA wordmark: a ringed serif V monogram and a spaced serif name. */
export function Logo({ href = "/", compact }: { href?: string; compact?: boolean }) {
  return (
    <Link href={href} className="group inline-flex items-center gap-2.5" aria-label="VIMORA">
      <span className="grid h-8 w-8 place-items-center rounded-full border border-accent/50 font-[family-name:var(--font-display)] text-[15px] italic text-accent transition-colors group-hover:bg-accent group-hover:text-white" aria-hidden>
        V
      </span>
      {!compact && <span className="font-[family-name:var(--font-display)] text-[20px] font-semibold tracking-[0.22em] text-ink">VIMORA</span>}
    </Link>
  );
}
