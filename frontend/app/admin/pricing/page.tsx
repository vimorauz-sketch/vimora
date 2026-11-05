"use client";

import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, CircleDashed, Lightbulb, Pencil, Plus, Search, Sparkles, Trash2, Wand2 } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CategoryIcon } from "@/components/category-icon";
import { Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Dialog, ErrorState, LoadingRows, PageHeader, Stat } from "@/components/ui/misc";
import { PrettySelect } from "@/components/ui/pretty-select";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";

type PType = "FIXED" | "PER_UNIT" | "QUANTITY_TIERED" | "STARTING_FROM" | "CUSTOM_QUOTE";
type Tier = { min_qty: number; unit_price_minor: number };
type Pricing = {
  pricing_type: PType; currency: string; base_price_minor: number; unit_label: Record<string, string>; min_quantity: number; max_quantity: number;
  tiers: Tier[]; addons: unknown[]; deposit_type: string; deposit_value: number;
};
type Row = {
  id: number; slug: string; name: string; is_active: boolean; mode: string; category: { slug: string; name: string; icon: string };
  pricing: Pricing | null; unpriced: boolean; suggested: Omit<Pricing, "addons" | "deposit_type" | "deposit_value"> | null;
};
type Data = { items: Row[]; unpriced: number; suggestable: number };
const TYPES: PType[] = ["FIXED", "PER_UNIT", "QUANTITY_TIERED", "STARTING_FROM", "CUSTOM_QUOTE"];
type Filter = "all" | "unpriced" | "differs";

export default function AdminPrices() {
  const { t, locale } = useI18n();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("services.manage");
  const q = useQuery({ queryKey: ["admin-pricing", locale], queryFn: () => api<Data>(`/admin/pricing?lang=${locale}`) });
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("all");
  const [filter, setFilter] = useState<Filter>("all");
  const [editing, setEditing] = useState<number | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const items = q.data?.items ?? [];
  const differs = (r: Row) => !!r.suggested && !!r.pricing && (r.pricing.pricing_type !== r.suggested.pricing_type || r.pricing.base_price_minor !== r.suggested.base_price_minor);
  const cats = useMemo(() => {
    const m = new Map<string, Row["category"]>();
    items.forEach((r) => m.set(r.category.slug, r.category));
    return [...m.values()];
  }, [items]);
  const needle = search.trim().toLocaleLowerCase();
  const shown = items.filter((r) => (cat === "all" || r.category.slug === cat)
    && (!needle || r.name.toLocaleLowerCase().includes(needle) || r.slug.includes(needle))
    && (filter === "all" || (filter === "unpriced" ? r.unpriced : differs(r))));
  const groups = cats.map((c, i) => ({ c, i, rows: shown.filter((r) => r.category.slug === c.slug) })).filter((g) => g.rows.length);
  const priced = items.filter((r) => !r.unpriced && r.pricing?.pricing_type !== "CUSTOM_QUOTE").length;

  async function fillAll() {
    setBusy(true);
    try {
      const r = await api<{ changed: number }>(`/admin/pricing/apply-suggested?lang=${locale}`, { body: {} });
      toast.success(t.pr.applied.replace("{n}", String(r.changed)));
      setConfirm(false);
      await q.refetch();
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title={t.pr.title} sub={t.pr.sub}
        actions={canManage && (q.data?.suggestable ?? 0) > 0 && <Button onClick={() => setConfirm(true)}><Wand2 className="h-4 w-4" aria-hidden />{t.pr.fillAll}</Button>} />

      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <Stat label={t.pr.priced} value={priced} icon={<BadgeCheck />} tint={3} />
        <Stat label={t.pr.individual} value={items.length - priced} icon={<CircleDashed />} tint={1} />
        <Stat label={t.pr.suggestable} value={q.data?.suggestable ?? 0} icon={<Sparkles />} tint={0} accent={(q.data?.suggestable ?? 0) > 0} />
      </div>
      <p className="mb-6 flex items-start gap-2.5 rounded-[16px] bg-tint-5 px-4 py-3 text-[13.5px] leading-relaxed"><Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />{t.pr.note}</p>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <label className="relative min-w-[240px] flex-1">
          <span className="sr-only">{t.pr.search}</span>
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t.pr.search}
            className="h-11 w-full rounded-full border border-border bg-surface pl-11 pr-4 text-[14px] shadow-[var(--shadow-soft)] focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10" />
        </label>
        <div className="w-full shrink-0 sm:w-[280px]"><PrettySelect value={cat} onValueChange={setCat} aria-label={t.admin.category}
          options={[{ value: "all", label: t.services.allCategories }, ...cats.map((c, i) => ({ value: c.slug, label: c.name, icon: <CategoryIcon name={c.icon} index={i} size="xs" /> }))]} /></div>
        <div className="flex gap-1 rounded-full border border-border bg-surface p-1" role="radiogroup" aria-label={t.pr.title}>
          {(Object.keys(t.pr.filters) as Filter[]).map((k) => (
            <button key={k} type="button" role="radio" aria-checked={filter === k} onClick={() => setFilter(k)}
              className={`rounded-full px-3.5 py-1.5 text-[13px] transition-colors ${filter === k ? "bg-ink text-ink-fg" : "text-muted hover:text-fg"}`}>{t.pr.filters[k]}</button>
          ))}
        </div>
      </div>

      {q.isLoading ? <LoadingRows rows={6} /> : q.error ? <ErrorState message={errorMessage(q.error, t)} /> : groups.length === 0 ? (
        <p className="card px-6 py-10 text-center text-muted">{t.pr.none}</p>
      ) : (
        <div className="space-y-6">
          {groups.map(({ c, i, rows }) => (
            <section key={c.slug} className="card overflow-hidden">
              <h2 className="flex items-center gap-3 border-b border-border bg-raised/30 px-5 py-3 text-[15px] font-semibold">
                <CategoryIcon name={c.icon} index={i} size="sm" />{c.name}<span className="ml-auto text-[12.5px] font-normal text-muted">{rows.length}</span>
              </h2>
              <ul className="divide-y divide-border">
                {rows.map((r) => (
                  <li key={r.id}>
                    {editing === r.id ? (
                      <Editor row={r} onClose={() => setEditing(null)} onSaved={async () => { setEditing(null); await q.refetch(); }} />
                    ) : (
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3.5">
                        <div className="min-w-[220px] flex-1">
                          <Link href={`/admin/services/${r.id}`} className="font-medium hover:underline">{r.name}</Link>
                          {!r.is_active && <span className="ml-2 rounded-full bg-raised px-2 py-0.5 text-[11px] text-muted">{t.pr.off}</span>}
                          {r.suggested && differs(r) && (
                            <span className="mt-0.5 block text-[12.5px] text-muted">{t.pr.suggested}: <PriceText p={r.suggested} /></span>
                          )}
                        </div>
                        <TypeChip type={r.unpriced ? "CUSTOM_QUOTE" : r.pricing?.pricing_type ?? "CUSTOM_QUOTE"} />
                        <div className="w-[190px] text-right text-[14.5px] font-semibold">
                          {r.pricing && !r.unpriced && r.pricing.pricing_type !== "CUSTOM_QUOTE" ? <PriceText p={r.pricing} /> : <span className="font-normal text-muted">{t.services.customQuote}</span>}
                        </div>
                        {canManage && (
                          <Button variant="outline" size="sm" onClick={() => setEditing(r.id)}><Pencil className="h-3.5 w-3.5" aria-hidden />{t.pr.edit}</Button>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <Dialog open={confirm} onOpenChange={setConfirm} title={t.pr.fillAll}
        footer={<><Button variant="outline" onClick={() => setConfirm(false)}>{t.pr.cancel}</Button><Button loading={busy} onClick={fillAll}>{t.pr.fillAll}</Button></>}>
        <p className="text-[14px] leading-relaxed">{t.pr.fillConfirm.replace("{n}", String(q.data?.suggestable ?? 0))}</p>
      </Dialog>
    </>
  );
}

function unitText(p: { unit_label: Record<string, string> }, locale: string) {
  return p.unit_label?.[locale] || p.unit_label?.uz || "";
}

function PriceText({ p }: { p: { pricing_type: PType; base_price_minor: number; currency: string; unit_label: Record<string, string>; tiers: Tier[] } }) {
  const { t, locale } = useI18n();
  if (p.pricing_type === "CUSTOM_QUOTE") return <>{t.services.customQuote}</>;
  const unit = unitText(p, locale);
  const from = p.pricing_type === "STARTING_FROM";
  return (
    <span className="tabular-nums">
      {from && locale !== "uz" && `${t.pr.fromWord} `}<Money minor={p.base_price_minor} currency={p.currency} />{from && locale === "uz" && ` ${t.pr.fromWord}`}
      {unit && <span className="font-normal text-muted"> / {unit}</span>}
      {p.tiers?.length > 0 && <span className="block text-[11.5px] font-normal text-ok">{p.tiers.map((x) => `${x.min_qty}+ → ${Math.round(x.unit_price_minor / 100).toLocaleString("ru-RU")}`).join(" · ")}</span>}
    </span>
  );
}

function TypeChip({ type }: { type: PType }) {
  const { t } = useI18n();
  const tone: Record<PType, string> = { FIXED: "bg-tint-3", PER_UNIT: "bg-tint-2", QUANTITY_TIERED: "bg-tint-4", STARTING_FROM: "bg-tint-0", CUSTOM_QUOTE: "bg-raised text-muted" };
  return <span className={`w-[150px] shrink-0 rounded-full px-3 py-1 text-center text-[12px] font-medium ${tone[type]}`}>{t.pr.types[type]}</span>;
}

function Editor({ row, onClose, onSaved }: { row: Row; onClose: () => void; onSaved: () => Promise<void> }) {
  const { t, locale } = useI18n();
  const init: Pricing = row.pricing ?? { pricing_type: "CUSTOM_QUOTE", currency: "UZS", base_price_minor: 0, unit_label: {}, min_quantity: 1, max_quantity: 1, tiers: [], addons: [], deposit_type: "PERCENT", deposit_value: 30 };
  const [p, setP] = useState<Pricing>({ ...init, tiers: [...(init.tiers ?? [])] });
  const [busy, setBusy] = useState(false);
  const set = (patch: Partial<Pricing>) => setP((x) => ({ ...x, ...patch }));
  const som = (minor: number) => (minor ? String(Math.round(minor / 100)) : "");
  const toMinor = (v: string) => Math.max(0, Math.round(Number(v.replace(/\D/g, "")) || 0)) * 100;
  const hasUnit = p.pricing_type === "PER_UNIT" || p.pricing_type === "QUANTITY_TIERED" || (p.pricing_type === "STARTING_FROM" && p.max_quantity > 1);
  const box = "h-10 rounded-[12px] border border-border bg-surface px-3 text-[14px] focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10";
  const field = `${box} w-full`;

  async function save(body: Pricing) {
    setBusy(true);
    try {
      const unit = body.unit_label ?? {};
      const payload = { ...body, unit_label: { uz: unit.uz ?? "", en: unit.en || unit.uz || "", ru: unit.ru || unit.uz || "" },
        tiers: body.pricing_type === "QUANTITY_TIERED" ? body.tiers.filter((x) => x.min_qty > 0 && x.unit_price_minor > 0) : [],
        base_price_minor: body.pricing_type === "CUSTOM_QUOTE" ? 0 : body.base_price_minor };
      await api(`/admin/pricing/${row.id}?lang=${locale}`, { method: "PUT", body: payload });
      toast.success(t.pr.saved);
      await onSaved();
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  async function useSuggested() {
    setBusy(true);
    try {
      await api(`/admin/pricing/apply-suggested?lang=${locale}`, { body: { service_ids: [row.id] } });
      toast.success(t.pr.saved);
      await onSaved();
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }

  return (
    <div className="bg-tint-0/30 px-5 py-5">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold">{row.name}</p>
        {row.suggested && <p className="text-[12.5px] text-muted">{t.pr.suggested}: <PriceText p={{ ...row.suggested, currency: "UZS" }} /></p>}
      </div>
      <div className="grid gap-2 sm:grid-cols-5" role="radiogroup" aria-label={t.admin.pricingType}>
        {TYPES.map((k) => (
          <button key={k} type="button" role="radio" aria-checked={p.pricing_type === k} onClick={() => set({ pricing_type: k })}
            className={`rounded-[14px] border p-3 text-left transition-all ${p.pricing_type === k ? "border-accent bg-surface shadow-[var(--shadow-soft)] ring-2 ring-accent/15" : "border-border bg-surface/60 hover:border-accent/40"}`}>
            <span className="block text-[13.5px] font-semibold">{t.pr.types[k]}</span>
            <span className="mt-0.5 block text-[11.5px] leading-snug text-muted">{t.pr.typeHints[k]}</span>
          </button>
        ))}
      </div>
      {p.pricing_type !== "CUSTOM_QUOTE" && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-[13px] font-medium lg:col-span-2">{t.pr.price}
            <input inputMode="numeric" className={`${field} mt-1.5 text-[15px] font-semibold tabular-nums`} value={som(p.base_price_minor)} onChange={(e) => set({ base_price_minor: toMinor(e.target.value) })} />
          </label>
          <label className="text-[13px] font-medium">{t.pr.unit}
            <input className={`${field} mt-1.5`} placeholder={t.pr.unitPh} value={p.unit_label?.[locale] ?? p.unit_label?.uz ?? ""} onChange={(e) => set({ unit_label: { ...p.unit_label, [locale]: e.target.value } })} disabled={!hasUnit} />
          </label>
          <label className="text-[13px] font-medium">{t.pr.minQty}
            <input type="number" min={1} className={`${field} mt-1.5`} value={p.min_quantity} onChange={(e) => set({ min_quantity: Math.max(1, Number(e.target.value) || 1) })} />
          </label>
          <label className="text-[13px] font-medium">{t.pr.maxQty}
            <input type="number" min={1} className={`${field} mt-1.5`} value={p.max_quantity} onChange={(e) => set({ max_quantity: Math.max(1, Number(e.target.value) || 1) })} />
          </label>
        </div>
      )}
      {p.pricing_type === "QUANTITY_TIERED" && (
        <div className="mt-4 rounded-[14px] border border-border bg-surface p-4">
          <p className="mb-2 text-[13px] font-semibold">{t.pr.tiers}</p>
          <ul className="space-y-2">
            {p.tiers.map((tier, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2 text-[13px]">
                <input type="number" min={2} aria-label={t.pr.tierFrom} className={`${box} w-24`} value={tier.min_qty} onChange={(e) => set({ tiers: p.tiers.map((x, j) => j === i ? { ...x, min_qty: Number(e.target.value) || 0 } : x) })} />
                <span className="text-muted">{t.pr.tierFrom} →</span>
                <input inputMode="numeric" aria-label={t.pr.tierPrice} className={`${box} w-36 tabular-nums`} value={som(tier.unit_price_minor)} onChange={(e) => set({ tiers: p.tiers.map((x, j) => j === i ? { ...x, unit_price_minor: toMinor(e.target.value) } : x) })} />
                <span className="text-muted">{t.pr.tierPrice}</span>
                <button type="button" onClick={() => set({ tiers: p.tiers.filter((_, j) => j !== i) })} className="grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-bg hover:text-danger" aria-label={t.common.delete}><Trash2 className="h-4 w-4" aria-hidden /></button>
              </li>
            ))}
          </ul>
          <Button type="button" variant="outline" size="sm" className="mt-3" onClick={() => set({ tiers: [...p.tiers, { min_qty: (p.tiers.at(-1)?.min_qty ?? 1) + 10, unit_price_minor: p.base_price_minor }] })}><Plus className="h-3.5 w-3.5" aria-hidden />{t.pr.addTier}</Button>
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-end gap-3">
        {p.deposit_type === "PERCENT" && (
          <label className="text-[13px] font-medium">{t.pr.deposit}
            <input type="number" min={0} max={100} className={`${box} mt-1.5 block w-28`} value={p.deposit_value} onChange={(e) => set({ deposit_value: Math.min(100, Math.max(0, Number(e.target.value) || 0)) })} />
          </label>
        )}
        <div className="ml-auto flex flex-wrap gap-2">
          {row.suggested && <Button variant="outline" disabled={busy} onClick={useSuggested}><Sparkles className="h-4 w-4" aria-hidden />{t.pr.useSuggested}</Button>}
          <Button variant="outline" onClick={onClose}>{t.pr.cancel}</Button>
          <Button loading={busy} onClick={() => save(p)}>{t.pr.save}</Button>
        </div>
      </div>
    </div>
  );
}
