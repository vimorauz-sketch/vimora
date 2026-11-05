"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { Confirm, ErrorState, LoadingRows, PageHeader, Panel, Switch } from "@/components/ui/misc";
import { MoneyInput } from "@/features/admin/money-input";
import { TInput, emptyT } from "@/features/admin/translatable";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { AdminArea, Translatable } from "@/types/api";

type RF = { key: string; label: Translatable; type: "text" | "textarea" | "number" | "url" | "select"; required: boolean; options: string[] };
type Addon = { key: string; label: Translatable; price_minor: number };
type Svc = {
  slug: string; category_id: number; name: Translatable; short_description: Translatable; description: Translatable; icon: string; image_attachment_id: number | null; estimated_delivery: Translatable;
  estimated_hours: number | null; required_fields: RF[]; allows_attachments: boolean; examples: unknown[]; is_active: boolean; is_featured: boolean; ai_eligible: boolean; ai_capability: string | null;
  revision_limit: number; sort_order: number; service_mode: "ONLINE" | "REMOTE" | "LOCAL" | "FUTURE" | "DISABLED" | null; service_area_id: number | null; requires_file: boolean;
  pricing: { pricing_type: string; currency: string; base_price_minor: number; unit_label: Translatable; min_quantity: number; max_quantity: number; tiers: { min_qty: number; unit_price_minor: number }[]; addons: Addon[]; deposit_type: string; deposit_value: number };
};

const blank = (): Svc => ({
  slug: "", category_id: 0, name: emptyT(), short_description: emptyT(), description: emptyT(), icon: "sparkles", image_attachment_id: null, estimated_delivery: emptyT(), estimated_hours: null,
  required_fields: [], allows_attachments: true, examples: [], is_active: false, is_featured: false, ai_eligible: false, ai_capability: null, revision_limit: 2, sort_order: 0,
  service_mode: "ONLINE", service_area_id: null, requires_file: false,
  pricing: { pricing_type: "CUSTOM_QUOTE", currency: "UZS", base_price_minor: 0, unit_label: emptyT(), min_quantity: 1, max_quantity: 1000, tiers: [], addons: [], deposit_type: "PERCENT", deposit_value: 30 },
});

export default function ServiceEditor() {
  const { t } = useI18n();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const isNew = id === "new";
  const cats = useQuery({ queryKey: ["admin-cats"], queryFn: () => api<{ items: { id: number; name: Translatable }[] }>("/admin/categories") });
  const areas = useQuery({ queryKey: ["admin-areas"], queryFn: () => api<{ items: AdminArea[] }>("/admin/areas") });
  const localAreas = (areas.data?.items ?? []).filter((a) => a.local_services_enabled);
  const svc = useQuery({ queryKey: ["admin-service", id], queryFn: () => api<Svc & { capabilities?: unknown; archived_at: string | null }>(`/admin/services/${id}`), enabled: !isNew });
  const caps = useQuery({ queryKey: ["admin-services", false], queryFn: () => api<{ capabilities: Record<string, string> }>("/admin/services") });
  const [s, setS] = useState<Svc>(blank);
  const [saving, setSaving] = useState(false);
  const imgRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (svc.data) { const d = svc.data; setS({ ...blank(), ...d, pricing: { ...blank().pricing, ...d.pricing }, required_fields: d.required_fields.map((f) => ({ ...f, options: f.options ?? [] })) }); } }, [svc.data]);
  useEffect(() => { if (isNew && cats.data?.items[0] && !s.category_id) setS((v) => ({ ...v, category_id: cats.data!.items[0]!.id })); }, [cats.data, isNew, s.category_id]);
  if (!isNew && svc.isLoading) return <LoadingRows rows={8} />;
  if (svc.error) return <ErrorState message={errorMessage(svc.error, t)} />;
  const p = s.pricing;
  const setP = (patch: Partial<Svc["pricing"]>) => setS({ ...s, pricing: { ...p, ...patch } });
  async function save() {
    setSaving(true);
    try {
      const { ...body } = s as Svc & Record<string, unknown>;
      ["id", "category", "image_url", "image_credit", "archived_at", "order_count", "capabilities", "mode", "availability_status", "service_area"].forEach((k) => delete (body as Record<string, unknown>)[k]);
      const r = await api<{ id: number }>(isNew ? "/admin/services" : `/admin/services/${id}`, { method: isNew ? "POST" : "PUT", body });
      toast.success(t.common.saved);
      if (isNew) router.replace(`/admin/services/${r.id}`); else void svc.refetch();
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setSaving(false); }
  }
  async function uploadImage() {
    const f = imgRef.current?.files?.[0];
    if (!f) return;
    const form = new FormData(); form.append("file", f);
    try { const r = await api<{ attachment_id: number }>("/admin/images", { form }); setS({ ...s, image_attachment_id: r.attachment_id }); } catch (e) { toast.error(errorMessage(e, t)); }
  }
  const priced = p.pricing_type !== "CUSTOM_QUOTE";
  return (
    <>
      <PageHeader title={isNew ? t.admin.newService : t.admin.editService} actions={<>
        {!isNew && (svc.data?.archived_at
          ? <Button variant="outline" onClick={async () => { await api(`/admin/services/${id}/restore`, { method: "POST" }); void svc.refetch(); }}>{t.admin.restore}</Button>
          : <Confirm danger title={t.admin.archive} confirmLabel={t.admin.archive} onConfirm={async () => { await api(`/admin/services/${id}/archive`, { method: "POST" }); router.push("/admin/services"); }} trigger={<Button variant="ghost">{t.admin.archive}</Button>} />)}
        <Button onClick={save} loading={saving}>{t.common.save}</Button>
      </>} />
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title={t.admin.name}>
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t.admin.slug}>{(fid) => <Input id={fid} value={s.slug} onChange={(e) => setS({ ...s, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })} />}</Field>
              <Field label={t.admin.category}>{(fid) => <Select id={fid} value={s.category_id} onChange={(e) => setS({ ...s, category_id: Number(e.target.value) })}>{cats.data?.items.map((c) => <option key={c.id} value={c.id}>{c.name.uz || c.name.en}</option>)}</Select>}</Field>
            </div>
            <div className="grid gap-3 rounded-[14px] border border-border bg-raised/40 p-4 sm:grid-cols-2">
              <Field label={t.biz.svc.mode}>{(fid) => (
                <Select id={fid} value={s.service_mode ?? "ONLINE"} onChange={(e) => setS({ ...s, service_mode: e.target.value as Svc["service_mode"], service_area_id: e.target.value === "LOCAL" ? s.service_area_id ?? localAreas[0]?.id ?? null : null })}>
                  {(["ONLINE", "REMOTE", "LOCAL", "FUTURE", "DISABLED"] as const).map((m) => <option key={m} value={m}>{m === "FUTURE" ? "FUTURE" : m === "DISABLED" ? "DISABLED (arxiv)" : t.biz.modes[m]} · {m}</option>)}
                </Select>
              )}</Field>
              {s.service_mode === "LOCAL" && (
                <Field label={t.biz.svc.area}>{(fid) => (
                  <Select id={fid} value={s.service_area_id ?? ""} onChange={(e) => setS({ ...s, service_area_id: e.target.value ? Number(e.target.value) : null })}>
                    {areas.data?.items.map((a) => <option key={a.id} value={a.id} disabled={!a.local_services_enabled}>{a.name.uz || a.name.en}{a.local_services_enabled ? "" : " —"}</option>)}
                  </Select>
                )}</Field>
              )}
              <div className="sm:col-span-2"><Switch label={t.biz.svc.requiresFile} checked={s.requires_file} onCheckedChange={(v) => setS({ ...s, requires_file: v })} /></div>
            </div>
            <TInput label={t.admin.name} value={s.name} onChange={(v) => setS({ ...s, name: v })} required />
            <TInput label={t.admin.shortDesc} value={s.short_description} onChange={(v) => setS({ ...s, short_description: v })} />
            <TInput label={t.admin.fullDesc} value={s.description} onChange={(v) => setS({ ...s, description: v })} multiline />
            <TInput label={t.admin.deliveryText} value={s.estimated_delivery} onChange={(v) => setS({ ...s, estimated_delivery: v })} />
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label={t.admin.icon}>{(fid) => <Input id={fid} value={s.icon} onChange={(e) => setS({ ...s, icon: e.target.value })} />}</Field>
              <Field label={t.admin.revisionLimit}>{(fid) => <Input id={fid} type="number" min={0} value={s.revision_limit} onChange={(e) => setS({ ...s, revision_limit: Number(e.target.value) })} />}</Field>
              <Field label="#">{(fid) => <Input id={fid} type="number" value={s.sort_order} onChange={(e) => setS({ ...s, sort_order: Number(e.target.value) })} />}</Field>
            </div>
            <div>
              <p className="mb-1.5 text-[13px] font-medium">{t.admin.image}{s.image_attachment_id ? ` #${s.image_attachment_id}` : ""}</p>
              <input ref={imgRef} type="file" accept=".png,.jpg,.jpeg,.webp" onChange={uploadImage} className="sr-only" aria-label={t.admin.image} />
              <Button type="button" size="sm" variant="outline" onClick={() => imgRef.current?.click()}>{t.common.upload}</Button>
            </div>
          </div>
        </Panel>
        <div className="space-y-6">
          <Panel title={t.services.price}>
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label={t.admin.pricingType}>{(fid) => <Select id={fid} value={p.pricing_type} onChange={(e) => setP({ pricing_type: e.target.value })}>{["FIXED", "PER_UNIT", "QUANTITY_TIERED", "STARTING_FROM", "CUSTOM_QUOTE"].map((x) => <option key={x}>{x}</option>)}</Select>}</Field>
                <Field label={t.admin.currency}>{(fid) => <Select id={fid} value={p.currency} onChange={(e) => setP({ currency: e.target.value })}><option>UZS</option><option>USD</option></Select>}</Field>
              </div>
              {priced && <Field label={`${t.admin.basePrice} (${p.currency})`}>{(fid) => <MoneyInput id={fid} value={p.base_price_minor} onChange={(m) => setP({ base_price_minor: m })} />}</Field>}
              {["PER_UNIT", "QUANTITY_TIERED", "STARTING_FROM"].includes(p.pricing_type) && (
                <>
                  <TInput label={t.admin.unitLabel} value={p.unit_label} onChange={(v) => setP({ unit_label: v })} />
                  <div className="grid grid-cols-2 gap-3">
                    <Field label={t.admin.minQty}>{(fid) => <Input id={fid} type="number" min={1} value={p.min_quantity} onChange={(e) => setP({ min_quantity: Number(e.target.value) })} />}</Field>
                    <Field label={t.admin.maxQty}>{(fid) => <Input id={fid} type="number" min={1} value={p.max_quantity} onChange={(e) => setP({ max_quantity: Number(e.target.value) })} />}</Field>
                  </div>
                </>
              )}
              {p.pricing_type === "QUANTITY_TIERED" && (
                <div className="space-y-2">
                  {p.tiers.map((tier, i) => (
                    <div key={i} className="grid grid-cols-[100px_1fr_36px] gap-2">
                      <Input aria-label={t.admin.minQty} type="number" min={1} value={tier.min_qty} onChange={(e) => setP({ tiers: p.tiers.map((x, j) => j === i ? { ...x, min_qty: Number(e.target.value) } : x) })} />
                      <MoneyInput aria-label={t.admin.unitPrice} value={tier.unit_price_minor} onChange={(m) => setP({ tiers: p.tiers.map((x, j) => j === i ? { ...x, unit_price_minor: m } : x) })} />
                      <Button variant="ghost" size="icon" aria-label={t.common.remove} onClick={() => setP({ tiers: p.tiers.filter((_, j) => j !== i) })}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  ))}
                  <Button size="sm" variant="ghost" onClick={() => setP({ tiers: [...p.tiers, { min_qty: 10, unit_price_minor: p.base_price_minor }] })}><Plus className="h-4 w-4" />tier</Button>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <Field label={t.admin.depositType}>{(fid) => <Select id={fid} value={p.deposit_type} onChange={(e) => setP({ deposit_type: e.target.value })}><option value="PERCENT">%</option><option value="FIXED">{t.admin.depositFixed}</option></Select>}</Field>
                <Field label={t.admin.depositValue}>{(fid) => p.deposit_type === "PERCENT"
                  ? <Input id={fid} type="number" min={0} max={100} value={p.deposit_value} onChange={(e) => setP({ deposit_value: Number(e.target.value) })} />
                  : <MoneyInput id={fid} value={p.deposit_value} onChange={(m) => setP({ deposit_value: m })} />}</Field>
              </div>
              {priced && (
                <div className="space-y-2 border-t border-border pt-3">
                  <p className="text-[13px] font-medium">{t.services.addons}</p>
                  {p.addons.map((a, i) => (
                    <div key={i} className="space-y-2 rounded-[6px] border border-border p-3">
                      <div className="grid grid-cols-[1fr_140px_36px] gap-2">
                        <Input aria-label={t.admin.fieldKey} value={a.key} onChange={(e) => setP({ addons: p.addons.map((x, j) => j === i ? { ...x, key: e.target.value } : x) })} />
                        <MoneyInput aria-label={t.services.price} value={a.price_minor} onChange={(m) => setP({ addons: p.addons.map((x, j) => j === i ? { ...x, price_minor: m } : x) })} />
                        <Button variant="ghost" size="icon" aria-label={t.common.remove} onClick={() => setP({ addons: p.addons.filter((_, j) => j !== i) })}><Trash2 className="h-4 w-4" /></Button>
                      </div>
                      <TInput label={t.admin.name} value={a.label} onChange={(v) => setP({ addons: p.addons.map((x, j) => j === i ? { ...x, label: v } : x) })} />
                    </div>
                  ))}
                  <Button size="sm" variant="ghost" onClick={() => setP({ addons: [...p.addons, { key: `extra_${p.addons.length + 1}`, label: emptyT(), price_minor: 0 }] })}><Plus className="h-4 w-4" />{t.services.addons}</Button>
                </div>
              )}
            </div>
          </Panel>
          <Panel title={t.common.status}>
            <Switch label={t.admin.active} checked={s.is_active} onCheckedChange={(v) => setS({ ...s, is_active: v })} />
            <Switch label={t.admin.featured} checked={s.is_featured} onCheckedChange={(v) => setS({ ...s, is_featured: v })} />
            <Switch label={t.admin.allowAttachments} checked={s.allows_attachments} onCheckedChange={(v) => setS({ ...s, allows_attachments: v })} />
            <Switch label={t.admin.aiEligible} checked={s.ai_eligible} onCheckedChange={(v) => setS({ ...s, ai_eligible: v, ai_capability: v ? s.ai_capability ?? Object.keys(caps.data?.capabilities ?? {})[0] ?? null : s.ai_capability })} />
            {s.ai_eligible && <Field label={t.admin.capability} className="mt-2">{(fid) => <Select id={fid} value={s.ai_capability ?? ""} onChange={(e) => setS({ ...s, ai_capability: e.target.value })}>{Object.entries(caps.data?.capabilities ?? {}).map(([k, d]) => <option key={k} value={k}>{k} — {d}</option>)}</Select>}</Field>}
          </Panel>
          <Panel title={t.admin.requiredFields}>
            <div className="space-y-3">
              {s.required_fields.map((f, i) => (
                <div key={i} className="space-y-2 rounded-[6px] border border-border p-3">
                  <div className="grid grid-cols-[1fr_120px_36px] gap-2">
                    <Input aria-label={t.admin.fieldKey} value={f.key} onChange={(e) => setS({ ...s, required_fields: s.required_fields.map((x, j) => j === i ? { ...x, key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_") } : x) })} />
                    <Select aria-label={t.admin.fieldType} value={f.type} onChange={(e) => setS({ ...s, required_fields: s.required_fields.map((x, j) => j === i ? { ...x, type: e.target.value as RF["type"] } : x) })}>{["text", "textarea", "number", "url", "select"].map((x) => <option key={x}>{x}</option>)}</Select>
                    <Button variant="ghost" size="icon" aria-label={t.common.remove} onClick={() => setS({ ...s, required_fields: s.required_fields.filter((_, j) => j !== i) })}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                  <TInput label={t.admin.name} value={f.label} onChange={(v) => setS({ ...s, required_fields: s.required_fields.map((x, j) => j === i ? { ...x, label: v } : x) })} />
                  {f.type === "select" && <Input aria-label="options" placeholder="a, b, c" value={f.options.join(", ")} onChange={(e) => setS({ ...s, required_fields: s.required_fields.map((x, j) => j === i ? { ...x, options: e.target.value.split(",").map((o) => o.trim()).filter(Boolean) } : x) })} />}
                  <Switch label={t.common.required} checked={f.required} onCheckedChange={(v) => setS({ ...s, required_fields: s.required_fields.map((x, j) => j === i ? { ...x, required: v } : x) })} />
                </div>
              ))}
              <Button size="sm" variant="ghost" onClick={() => setS({ ...s, required_fields: [...s.required_fields, { key: `field_${s.required_fields.length + 1}`, label: emptyT(), type: "text", required: true, options: [] }] })}><Plus className="h-4 w-4" />{t.admin.addField}</Button>
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}
