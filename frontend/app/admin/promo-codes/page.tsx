"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { Dialog, PageHeader, Switch, Table } from "@/components/ui/misc";
import { MoneyInput } from "@/features/admin/money-input";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";

type Promo = { id: number; code: string; percent_off: number | null; amount_off_minor: number | null; currency: string | null; max_uses: number | null; max_uses_per_user: number; min_order_minor: number; valid_from: string | null; valid_until: string | null; is_active: boolean; service_ids: number[]; uses: number };
const blank: Promo = { id: 0, code: "", percent_off: 10, amount_off_minor: null, currency: null, max_uses: null, max_uses_per_user: 1, min_order_minor: 0, valid_from: null, valid_until: null, is_active: true, service_ids: [], uses: 0 };

export default function Promos() {
  const { t, locale } = useI18n();
  const q = useQuery({ queryKey: ["promos"], queryFn: () => api<{ items: Promo[] }>("/admin/promo-codes") });
  const [p, setP] = useState<Promo | null>(null);
  const [kind, setKind] = useState<"pct" | "amt">("pct");
  async function save() {
    if (!p) return;
    const { id, uses, ...body } = p; void uses;
    if (kind === "pct") { body.amount_off_minor = null; body.currency = null; } else { body.percent_off = null; body.currency = body.currency ?? "UZS"; }
    try { await api(id ? `/admin/promo-codes/${id}` : "/admin/promo-codes", { method: id ? "PUT" : "POST", body }); setP(null); void q.refetch(); } catch (e) { toast.error(errorMessage(e, t)); }
  }
  return (
    <>
      <PageHeader title={t.admin.promos} actions={<Button onClick={() => { setKind("pct"); setP(blank); }}>{t.admin.newPromo}</Button>} />
      <Table head={[t.admin.code, t.dash.discount, t.admin.uses, t.admin.validUntil, t.common.status]}>
        {q.data?.items.map((x) => (
          <tr key={x.id} className="cursor-pointer hover:bg-surface" onClick={() => { setKind(x.percent_off ? "pct" : "amt"); setP(x); }}>
            <td className="px-4 py-3 font-medium">{x.code}</td>
            <td className="px-4 py-3">{x.percent_off ? `${x.percent_off}%` : `${(x.amount_off_minor ?? 0) / 100} ${x.currency}`}</td>
            <td className="px-4 py-3 tabular-nums">{x.uses}{x.max_uses ? ` / ${x.max_uses}` : ""}</td>
            <td className="px-4 py-3">{date(x.valid_until, locale)}</td>
            <td className="px-4 py-3">{x.is_active ? <span className="text-ok">{t.admin.active}</span> : "off"}</td>
          </tr>
        ))}
      </Table>
      {p && (
        <Dialog open onOpenChange={(o) => !o && setP(null)} title={p.id ? p.code : t.admin.newPromo} footer={<Button onClick={save}>{t.common.save}</Button>}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t.admin.code} className="sm:col-span-2">{(id) => <Input id={id} value={p.code} onChange={(e) => setP({ ...p, code: e.target.value.toUpperCase() })} />}</Field>
            <Field label={t.dash.discount}>{(id) => <Select id={id} value={kind} onChange={(e) => setKind(e.target.value as "pct" | "amt")}><option value="pct">{t.admin.percentOff}</option><option value="amt">{t.admin.amountOff}</option></Select>}</Field>
            {kind === "pct" ? <Field label="%">{(id) => <Input id={id} type="number" min={1} max={100} value={p.percent_off ?? ""} onChange={(e) => setP({ ...p, percent_off: Number(e.target.value) })} />}</Field>
              : <Field label={`${t.common.amount} (${p.currency ?? "UZS"})`}>{(id) => <MoneyInput id={id} value={p.amount_off_minor ?? 0} onChange={(m) => setP({ ...p, amount_off_minor: m })} />}</Field>}
            {kind === "amt" && <Field label={t.admin.currency}>{(id) => <Select id={id} value={p.currency ?? "UZS"} onChange={(e) => setP({ ...p, currency: e.target.value })}><option>UZS</option><option>USD</option></Select>}</Field>}
            <Field label={t.admin.maxUses}>{(id) => <Input id={id} type="number" min={1} value={p.max_uses ?? ""} onChange={(e) => setP({ ...p, max_uses: e.target.value ? Number(e.target.value) : null })} />}</Field>
            <Field label={t.admin.perUser}>{(id) => <Input id={id} type="number" min={1} value={p.max_uses_per_user} onChange={(e) => setP({ ...p, max_uses_per_user: Number(e.target.value) })} />}</Field>
            <Field label={t.admin.validFrom}>{(id) => <Input id={id} type="date" value={p.valid_from?.slice(0, 10) ?? ""} onChange={(e) => setP({ ...p, valid_from: e.target.value ? new Date(e.target.value).toISOString() : null })} />}</Field>
            <Field label={t.admin.validUntil}>{(id) => <Input id={id} type="date" value={p.valid_until?.slice(0, 10) ?? ""} onChange={(e) => setP({ ...p, valid_until: e.target.value ? new Date(e.target.value).toISOString() : null })} />}</Field>
            <div className="sm:col-span-2"><Switch label={t.admin.active} checked={p.is_active} onCheckedChange={(v) => setP({ ...p, is_active: v })} /></div>
          </div>
        </Dialog>
      )}
    </>
  );
}
