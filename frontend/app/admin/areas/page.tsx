"use client";

import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Dialog, ErrorState, LoadingRows, PageHeader, Switch, Table } from "@/components/ui/misc";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { AdminArea, Translatable } from "@/types/api";

type Form = {
  id?: number; slug: string; kind: AdminArea["kind"]; name: Translatable; region: string; district: string; locality: string; is_active: boolean;
  local_services_enabled: boolean; provider_id: number | null; rules: Translatable; pickup_address: string; sort_order: number;
};
const EMPTY: Form = { slug: "", kind: "LOCALITY", name: { uz: "", en: "", ru: "" }, region: "Jizzax viloyati", district: "", locality: "", is_active: true,
  local_services_enabled: false, provider_id: null, rules: { uz: "", en: "", ru: "" }, pickup_address: "", sort_order: 50 };

export default function AreasPage() {
  const { t, locale } = useI18n();
  const A = t.biz.areas;
  const { data: me } = useMe();
  const canEdit = !!me?.permissions.includes("settings.manage");
  const q = useQuery({ queryKey: ["admin-areas"], queryFn: () => api<{ items: AdminArea[] }>("/admin/areas") });
  const [form, setForm] = useState<Form | null>(null);
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof Form>(k: K, v: Form[K]) => setForm((f) => (f ? { ...f, [k]: v } : f));

  async function save() {
    if (!form) return;
    setBusy(true);
    const { id, ...body } = form;
    try {
      await api(id ? `/admin/areas/${id}` : "/admin/areas", { method: id ? "PUT" : "POST", body: { ...body, pickup_address: body.pickup_address ?? "" } });
      toast.success(t.common.saved);
      setForm(null);
      void q.refetch();
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title={A.title} sub={A.sub} actions={canEdit && <Button onClick={() => setForm({ ...EMPTY })}>{A.add}</Button>} />
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} onRetry={() => q.refetch()} /> : (
        <Table head={[A.name, A.kind, A.district, A.local, A.services, ""]} empty={!q.data?.items.length}>
          {q.data?.items.map((a) => (
            <tr key={a.id} className="border-t border-border">
              <td className="px-4 py-3">
                <span className="flex items-center gap-2 font-medium">{a.local_services_enabled && <MapPin className="h-4 w-4 text-accent" aria-hidden />}{a.name[locale] || a.name.uz}</span>
                <span className="text-[12.5px] text-muted">{a.slug}{!a.is_active && ` · ${A.inactive}`}</span>
              </td>
              <td className="px-4 py-3">{A.kinds[a.kind]}</td>
              <td className="px-4 py-3 text-muted">{[a.region, a.district, a.locality].filter(Boolean).join(" · ")}</td>
              <td className="px-4 py-3">{a.local_services_enabled ? <span className="rounded-full bg-tint-0 px-2.5 py-0.5 text-[12.5px] font-medium text-accent">✓</span> : <span className="text-muted">—</span>}</td>
              <td className="px-4 py-3 tabular-nums">{a.service_count}</td>
              <td className="px-4 py-3 text-right">
                {canEdit && <Button size="sm" variant="ghost" onClick={() => setForm({ id: a.id, slug: a.slug, kind: a.kind, name: a.name, region: a.region, district: a.district, locality: a.locality,
                  is_active: a.is_active, local_services_enabled: a.local_services_enabled, provider_id: a.provider_id, rules: a.rules, pickup_address: a.pickup_address ?? "", sort_order: a.sort_order })}>{A.edit}</Button>}
              </td>
            </tr>
          ))}
        </Table>
      )}
      <Dialog open={!!form} onOpenChange={(o) => !o && setForm(null)} title={form?.id ? A.edit : A.add} wide
        footer={<><Button variant="ghost" onClick={() => setForm(null)}>{t.common.cancel}</Button><Button onClick={save} loading={busy}>{t.common.save}</Button></>}>
        {form && (
          <div className="grid gap-4 sm:grid-cols-2">
            {(["uz", "en", "ru"] as const).map((l) => (
              <Field key={l} label={`${A.name} (${l})`}>{(id) => <Input id={id} value={form.name[l]} onChange={(e) => set("name", { ...form.name, [l]: e.target.value })} maxLength={120} />}</Field>
            ))}
            <Field label={A.slug}>{(id) => <Input id={id} value={form.slug} onChange={(e) => set("slug", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} maxLength={80} />}</Field>
            <Field label={A.kind}>{(id) => <Select id={id} value={form.kind} onChange={(e) => set("kind", e.target.value as Form["kind"])}>{(Object.keys(A.kinds) as Form["kind"][]).map((k) => <option key={k} value={k}>{A.kinds[k]}</option>)}</Select>}</Field>
            <Field label={A.region}>{(id) => <Input id={id} value={form.region} onChange={(e) => set("region", e.target.value)} maxLength={120} />}</Field>
            <Field label={A.district}>{(id) => <Input id={id} value={form.district} onChange={(e) => set("district", e.target.value)} maxLength={120} />}</Field>
            <Field label={A.locality}>{(id) => <Input id={id} value={form.locality} onChange={(e) => set("locality", e.target.value)} maxLength={120} />}</Field>
            <Field label={A.provider}>{(id) => <Select id={id} value={form.provider_id ?? ""} onChange={(e) => set("provider_id", e.target.value ? Number(e.target.value) : null)}>
              <option value="">{A.owner}</option>
              {me && <option value={me.user.id}>{me.user.full_name || me.user.email}</option>}
            </Select>}</Field>
            <div className="sm:col-span-2 space-y-1">
              <Switch label={A.active} checked={form.is_active} onCheckedChange={(v) => set("is_active", v)} />
              <Switch label={A.local} checked={form.local_services_enabled} onCheckedChange={(v) => set("local_services_enabled", v)} />
            </div>
            <div className="sm:col-span-2">
              <Field label={A.pickup}>{(id) => <Textarea id={id} value={form.pickup_address} onChange={(e) => set("pickup_address", e.target.value)} maxLength={1000} className="min-h-[72px]" />}</Field>
              <p className="mt-1 text-[12.5px] text-muted">{A.pickupHint}</p>
            </div>
            <div className="sm:col-span-2">
              <Field label={`${A.rules} (uz)`} optional={t.common.optional}>{(id) => <Input id={id} value={form.rules.uz} onChange={(e) => set("rules", { ...form.rules, uz: e.target.value })} maxLength={300} />}</Field>
            </div>
          </div>
        )}
      </Dialog>
    </>
  );
}
