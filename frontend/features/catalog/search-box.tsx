"use client";

import { ArrowRight, CornerDownLeft, LayoutGrid, Loader2, Search, SearchX, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { CategoryIcon } from "@/components/category-icon";
import { ModeBadge } from "@/components/mode-badge";
import { priceLabel } from "@/features/service-card";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { Category, Paged, Service } from "@/types/api";

type Item = { key: string; href: string };
const APOS = /[‘’ʻʼ`]/g;
const fold = (s: string) => s.toLocaleLowerCase().replace(APOS, "'");

/**
 * Catalog search. Focusing it opens a panel with all categories; typing (even one letter)
 * shows matching services and categories live. Enter / the button opens the full results page.
 */
export function SearchBox({ cats, defaultValue = "", hidden }: { cats: Category[]; defaultValue?: string; hidden?: Record<string, string | undefined> }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const id = useId();
  const [q, setQ] = useState(defaultValue);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [res, setRes] = useState<{ q: string; items: Service[]; total: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const term = q.trim();

  const list = useMemo(() => cats.filter((c) => (c.service_count ?? 0) > 0), [cats]);
  const tint = (slug: string) => Math.max(0, list.findIndex((c) => c.slug === slug));
  const catHits = term ? list.filter((c) => fold(c.name).includes(fold(term))).slice(0, 4) : list;

  // live results, debounced; stale answers are ignored
  useEffect(() => {
    if (!term) { setRes(null); setLoading(false); return; }
    setLoading(true);
    const ctl = { stale: false };
    const h = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ q: term, lang: locale, page_size: "6" });
        const d = await api<Paged<Service>>(`/catalog/services?${qs}`);
        if (!ctl.stale) setRes({ q: term, items: d.items, total: d.total });
      } catch {
        if (!ctl.stale) setRes({ q: term, items: [], total: 0 });
      } finally {
        if (!ctl.stale) setLoading(false);
      }
    }, 180);
    return () => { ctl.stale = true; clearTimeout(h); };
  }, [term, locale]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const fullHref = () => {
    const p = new URLSearchParams();
    Object.entries(hidden ?? {}).forEach(([k, v]) => v && p.set(k, v));
    if (term) p.set("q", term); else p.delete("q");
    return `/services${p.size ? `?${p}` : ""}`;
  };
  const services = term ? res?.items ?? [] : [];
  const items: Item[] = [
    ...services.map((s) => ({ key: `s-${s.slug}`, href: `/services/${s.slug}` })),
    ...catHits.map((c) => ({ key: `c-${c.slug}`, href: `/services?category=${c.slug}` })),
    ...(term ? [{ key: "all", href: fullHref() }] : []),
  ];
  const idx = (key: string) => items.findIndex((i) => i.key === key);
  const go = (href: string) => { setOpen(false); router.push(href); };

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Escape") { setOpen(false); return; }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      if (!items.length) return;
      setActive((a) => (e.key === "ArrowDown" ? (a + 1) % items.length : (a <= 0 ? items.length - 1 : a - 1)));
    }
    if (e.key === "Enter" && open && active >= 0 && items[active]) { e.preventDefault(); go(items[active].href); }
  }
  const optCls = (key: string) => `${idx(key) === active ? "bg-tint-0" : "hover:bg-bg"}`;
  const listId = `${id}-list`;

  return (
    <div ref={wrap} className="relative">
      <form action="/services" role="search" className="group relative flex items-center" onSubmit={(e) => { e.preventDefault(); go(fullHref()); }}>
        {Object.entries(hidden ?? {}).map(([k, v]) => v ? <input key={k} type="hidden" name={k} value={v} /> : null)}
        <Search className="pointer-events-none absolute left-5 h-5 w-5 text-muted transition-colors group-focus-within:text-accent" aria-hidden />
        <label htmlFor={id} className="sr-only">{t.common.search}</label>
        <input ref={input} id={id} name="q" type="search" value={q} placeholder={t.services.searchBig} maxLength={100} autoComplete="off"
          role="combobox" aria-expanded={open} aria-controls={listId} aria-autocomplete="list"
          aria-activedescendant={open && active >= 0 && items[active] ? `${id}-${items[active].key}` : undefined}
          onFocus={() => setOpen(true)} onClick={() => setOpen(true)} onKeyDown={onKey}
          onChange={(e) => { setQ(e.target.value); setActive(-1); setOpen(true); }}
          className={`h-14 w-full border border-border bg-surface pl-14 pr-[150px] text-[15px] shadow-[var(--shadow-soft)] transition-all placeholder:text-muted/70 hover:border-accent/40 focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10 [&::-webkit-search-cancel-button]:hidden ${open ? "rounded-[28px]" : "rounded-full"}`} />
        {q && (
          <button type="button" onClick={() => { setQ(""); input.current?.focus(); }} aria-label={t.services.clear}
            className="absolute right-[124px] grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-bg hover:text-fg">
            <X className="h-4 w-4" aria-hidden />
          </button>
        )}
        <button type="submit" className="absolute right-1.5 inline-flex h-11 items-center gap-2 rounded-full bg-accent px-6 text-[14.5px] font-medium text-accent-fg shadow-[var(--shadow-soft)] transition-colors hover:bg-accent-hover">
          {t.common.search}
        </button>
      </form>

      {open && (
        <div id={listId} role="listbox" aria-label={t.services.categoriesTitle}
          className="absolute inset-x-0 top-[calc(100%+10px)] z-40 max-h-[min(560px,70vh)] overflow-y-auto rounded-[24px] border border-border bg-surface p-3 shadow-[var(--shadow-lift)] animate-[vimora-pop_.2s_ease-out]">
          {term && (
            <section aria-label={t.services.title}>
              <p className="flex items-center justify-between px-3 pb-2 pt-1 text-[11.5px] font-semibold uppercase tracking-[0.12em] text-muted">
                <span>{t.services.title}</span>
                {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : res && <span className="normal-case tracking-normal">{t.services.found.replace("{n}", String(res.total))}</span>}
              </p>
              {services.length > 0 ? (
                <ul>
                  {services.map((s) => (
                    <li key={s.slug} id={`${id}-s-${s.slug}`} role="option" aria-selected={idx(`s-${s.slug}`) === active}>
                      <Link href={`/services/${s.slug}`} onClick={() => setOpen(false)} onMouseEnter={() => setActive(idx(`s-${s.slug}`))}
                        className={`flex items-center gap-3 rounded-[16px] px-3 py-2.5 transition-colors ${optCls(`s-${s.slug}`)}`}>
                        <CategoryIcon name={s.category.icon} index={tint(s.category.slug)} size="sm" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[14.5px] font-medium"><Highlight text={s.name} term={term} /></span>
                          <span className="block truncate text-[12.5px] text-muted">{s.category.name} · {priceLabel(s, t, locale)}</span>
                        </span>
                        <span className="hidden shrink-0 sm:block"><ModeBadge s={s} t={t} /></span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : !loading && res ? (
                <div className="flex items-center gap-3 rounded-[16px] bg-bg px-4 py-4 text-[13.5px]">
                  <SearchX className="h-5 w-5 shrink-0 text-muted" aria-hidden />
                  <span className="flex-1">{t.services.none}</span>
                  <Link href="/custom-order" onClick={() => setOpen(false)} className="shrink-0 font-medium text-accent hover:underline">{t.services.noneCta}</Link>
                </div>
              ) : null}
            </section>
          )}

          {catHits.length > 0 && (
            <section aria-label={t.services.categoriesTitle} className={term ? "mt-2 border-t border-border pt-2" : ""}>
              <p className="px-3 pb-2 pt-1 text-[11.5px] font-semibold uppercase tracking-[0.12em] text-muted">{t.services.categoriesTitle}</p>
              <ul className={term ? "" : "grid gap-1 sm:grid-cols-2 lg:grid-cols-3"}>
                {!term && (
                  <li>
                    <Link href="/services" onClick={() => setOpen(false)} className="flex items-center gap-3 rounded-[16px] px-3 py-2 hover:bg-bg">
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-ink text-ink-fg"><LayoutGrid className="h-4 w-4" aria-hidden /></span>
                      <span className="flex-1 text-[14px] font-medium">{t.services.allCategories}</span>
                    </Link>
                  </li>
                )}
                {catHits.map((c) => (
                  <li key={c.slug} id={`${id}-c-${c.slug}`} role="option" aria-selected={idx(`c-${c.slug}`) === active}>
                    <Link href={`/services?category=${c.slug}`} onClick={() => setOpen(false)} onMouseEnter={() => setActive(idx(`c-${c.slug}`))}
                      className={`flex items-center gap-3 rounded-[16px] px-3 py-2 transition-colors ${optCls(`c-${c.slug}`)}`}>
                      <CategoryIcon name={c.icon} index={tint(c.slug)} size="sm" />
                      <span className="min-w-0 flex-1 text-[14px] leading-snug"><Highlight text={c.name} term={term} /></span>
                      <span className="rounded-full bg-bg px-2 py-0.5 text-[11.5px] tabular-nums text-muted">{c.service_count}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {term && (
            <Link href={fullHref()} id={`${id}-all`} role="option" aria-selected={idx("all") === active} onClick={() => setOpen(false)} onMouseEnter={() => setActive(idx("all"))}
              className={`mt-2 flex items-center justify-between gap-3 rounded-[16px] border border-border px-4 py-3 text-[14px] font-medium transition-colors ${idx("all") === active ? "border-accent/50 bg-tint-0" : "hover:border-accent/40"}`}>
              <span className="truncate">{t.services.allResults.replace("{q}", term)}</span>
              <span className="flex shrink-0 items-center gap-2 text-[12px] text-muted"><CornerDownLeft className="h-3.5 w-3.5" aria-hidden /><ArrowRight className="h-4 w-4 text-accent" aria-hidden /></span>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

function Highlight({ text, term }: { text: string; term: string }) {
  if (!term) return <>{text}</>;
  const i = fold(text).indexOf(fold(term));
  if (i < 0) return <>{text}</>;
  return <>{text.slice(0, i)}<mark className="rounded-[3px] bg-accent/15 text-inherit">{text.slice(i, i + term.length)}</mark>{text.slice(i + term.length)}</>;
}
