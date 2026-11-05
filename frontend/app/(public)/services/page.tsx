import Link from "next/link";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Globe, LayoutGrid, MapPin, MonitorSmartphone, Navigation, Search, SearchX, X } from "lucide-react";
import { CategoryIcon } from "@/components/category-icon";
import { SearchBox } from "@/features/catalog/search-box";
import { AreaPicker } from "@/features/local/area-picker";
import { Button } from "@/components/ui/button";
import { ServiceCard } from "@/features/service-card";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";
import type { Category, Paged, Service } from "@/types/api";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.services.title, description: t.services.sub, alternates: { canonical: "/services" } };
}

export default async function ServicesPage({ searchParams }: { searchParams: Promise<{ q?: string; category?: string; page?: string; mode?: string; mine?: string }> }) {
  const sp = await searchParams;
  const { t, locale } = await getServerDict();
  const page = Math.max(1, Number(sp.page) || 1);
  const qs = new URLSearchParams({ lang: locale, page: String(page), page_size: "24" });
  if (sp.q) qs.set("q", sp.q.slice(0, 100));
  if (sp.category) qs.set("category", sp.category.slice(0, 80));
  const mode = ["ONLINE", "REMOTE", "LOCAL"].includes(sp.mode ?? "") ? sp.mode : undefined;
  if (mode) qs.set("mode", mode);
  const myArea = (await cookies()).get("vimora_area")?.value?.match(/^[a-z0-9-]{1,80}$/)?.[0];
  const mine = sp.mine === "1";
  if (mine && myArea) qs.set("area", myArea);
  const [data, cats] = await Promise.all([serverGet<Paged<Service>>(`/catalog/services?${qs}`, { revalidate: 30 }), serverGet<{ items: Category[] }>(`/catalog/categories?lang=${locale}`)]);
  const link = (patch: Record<string, string | undefined>) => {
    const p = new URLSearchParams();
    const merged = { q: sp.q, category: sp.category, mode, mine: mine ? "1" : undefined, ...patch };
    Object.entries(merged).forEach(([k, v]) => v && p.set(k, v));
    return `/services${p.size ? `?${p}` : ""}`;
  };
  const pages = data ? Math.ceil(data.total / 24) : 1;
  const chip = (active: boolean) => `inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full border px-4 py-2 text-[13.5px] transition-all ${active ? "border-ink bg-ink text-ink-fg shadow-[var(--shadow-soft)]" : "border-border bg-surface text-fg hover:border-accent/60 hover:shadow-[var(--shadow-soft)]"}`;
  const modeIcon = { all: <LayoutGrid className="h-4 w-4" aria-hidden />, ONLINE: <Globe className="h-4 w-4" aria-hidden />, REMOTE: <MonitorSmartphone className="h-4 w-4" aria-hidden />, LOCAL: <MapPin className="h-4 w-4" aria-hidden /> };
  const shownCats = (cats?.items ?? []).filter((c) => (c.service_count ?? 0) > 0);
  const catIndex = shownCats.findIndex((c) => c.slug === sp.category);
  const activeCat = catIndex >= 0 ? shownCats[catIndex] : undefined;
  const filtered = !!(sp.q || sp.category || mode || mine);
  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-16 pt-8 sm:px-8">
      {/* search band */}
      <section className="warm-glow relative z-20 rounded-[28px] border border-border bg-surface/60 px-5 py-8 sm:px-10 sm:py-12">
        <h1 className="display text-[34px] sm:text-[48px]">{t.services.title}</h1>
        <p className="mt-2 max-w-[60ch] text-muted">{t.services.sub}</p>
        <div className="mt-7 grid gap-3 lg:grid-cols-[1fr_300px]">
          <div className="relative z-30"><SearchBox key={sp.q ?? ""} cats={cats?.items ?? []} defaultValue={sp.q ?? ""} hidden={{ category: sp.category, mode }} /></div>
          <AreaPicker size="lg" className="!h-14 !rounded-full" />
        </div>
        <nav aria-label={t.biz.method} className="-mx-1 mt-5 flex gap-2 overflow-x-auto px-1 pb-1">
          {([["all", undefined], ["ONLINE", "ONLINE"], ["REMOTE", "REMOTE"], ["LOCAL", "LOCAL"]] as const).map(([k, m]) => {
            const active = !mine && mode === m;
            return (
              <Link key={k} href={link({ mode: m, mine: undefined, page: undefined })} aria-current={active ? "page" : undefined} className={chip(active)}>
                {modeIcon[k]}{t.biz.filters[k]}
              </Link>
            );
          })}
          <Link href={link({ mine: "1", mode: undefined, page: undefined })} aria-current={mine ? "page" : undefined}
            className={`${chip(false)} ${mine ? "!border-accent !bg-accent !text-accent-fg" : ""}`}>
            <Navigation className="h-4 w-4" aria-hidden />{t.biz.filters.mine}
          </Link>
        </nav>
        {mine && !myArea && <p className="mt-4 rounded-[14px] bg-tint-5 px-4 py-3 text-[14px]">{t.biz.noAreaForMine}</p>}
      </section>

      <div className="mt-8">
      <section aria-live="polite">
        {data && (
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {activeCat && (
                <Link href={link({ category: undefined, page: undefined })} className="inline-flex items-center gap-2 rounded-full border border-border bg-surface py-1 pl-1 pr-3 text-[13.5px] shadow-[var(--shadow-soft)] hover:border-accent/50">
                  <CategoryIcon name={activeCat.icon} index={catIndex} size="xs" />{activeCat.name}<X className="h-3.5 w-3.5 text-muted" aria-hidden />
                </Link>
              )}
              <p className="text-[14px] text-muted">{t.services.found.replace("{n}", String(data.total))}{sp.q ? <> · «<span className="text-fg">{sp.q}</span>»</> : null}</p>
            </div>
            {filtered && <Link href="/services" className="inline-flex items-center gap-1.5 text-[13.5px] text-muted hover:text-fg"><X className="h-3.5 w-3.5" aria-hidden />{t.services.clear}</Link>}
          </div>
        )}
        {!data ? (
          <p className="text-muted">{t.common.error}</p>
        ) : data.items.length === 0 ? (
          <div className="card flex flex-col items-center px-6 py-14 text-center">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-tint-0 text-accent"><SearchX className="h-6 w-6" aria-hidden /></span>
            <p className="mt-4 text-[16px] font-medium">{t.services.none}</p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <Button asChild><Link href="/custom-order">{t.services.noneCta}</Link></Button>
              {filtered && <Button asChild variant="outline"><Link href="/services">{t.services.clear}</Link></Button>}
            </div>
          </div>
        ) : (
          <>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{data.items.map((s) => <ServiceCard key={s.id} s={s} t={t} locale={locale} />)}</div>
            {pages > 1 && (
              <div className="mt-10 flex items-center justify-center gap-2">
                {page > 1 && <Button asChild variant="outline" size="sm"><Link href={link({ page: String(page - 1) })}>{t.common.prev}</Link></Button>}
                <span className="px-3 text-[13px] text-muted tabular-nums">{page} / {pages}</span>
                {page < pages && <Button asChild variant="outline" size="sm"><Link href={link({ page: String(page + 1) })}>{t.common.next}</Link></Button>}
              </div>
            )}
          </>
        )}
      </section>
      </div>
    </div>
  );
}
