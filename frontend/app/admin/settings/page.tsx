"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { ErrorState, LoadingRows, Notice, PageHeader, Panel, Switch } from "@/components/ui/misc";
import { TInput, emptyT } from "@/features/admin/translatable";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { Translatable } from "@/types/api";

type S = { values: Record<string, unknown>; integrations: Record<string, boolean>; environment: Record<string, unknown>; production_problems: string[] };
const ADMIN_EVENTS = ["order.created", "custom_request.created", "quotation.accepted", "payment.deposit_received", "payment.failed", "ai.started", "ai.completed", "ai.failed", "review.required", "message.received", "revision.requested", "payment.final_received", "order.cancelled"];

export default function Settings() {
  const { t } = useI18n();
  const { data: me } = useMe();
  const q = useQuery({ queryKey: ["settings"], queryFn: () => api<S>("/admin/settings") });
  const [v, setV] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState<Set<string>>(new Set());
  useEffect(() => { if (q.data) setV(q.data.values); }, [q.data]);
  if (q.isLoading) return <LoadingRows rows={6} />;
  if (q.error || !q.data) return <ErrorState message={errorMessage(q.error, t)} />;
  const set = (k: string, val: unknown) => { setV({ ...v, [k]: val }); setDirty(new Set(dirty).add(k)); };
  const b = (k: string) => Boolean(v[k]);
  const s = (k: string) => String(v[k] ?? "");
  const tr = (k: string) => ({ ...emptyT(), ...((v[k] as Translatable) ?? {}) });
  async function save() {
    const values = Object.fromEntries([...dirty].map((k) => [k, v[k]]));
    try { await api("/admin/settings", { method: "PATCH", body: { values } }); setDirty(new Set()); toast.success(t.common.saved); void q.refetch(); } catch (e) { toast.error(errorMessage(e, t)); }
  }
  const test = async (path: string) => { try { const r = await api<{ ok: boolean; error?: string; result?: string }>(path, { method: "POST" }); r.ok ? toast.success("OK") : toast.error(r.error ?? r.result ?? "Failed"); } catch (e) { toast.error(errorMessage(e, t)); } };
  const events = (v["notifications.telegram_admin_events"] as string[]) ?? [];
  return (
    <>
      <PageHeader title={t.admin.settings} actions={<Button onClick={save} disabled={!dirty.size}>{t.common.save}{dirty.size ? ` (${dirty.size})` : ""}</Button>} />
      {q.data.production_problems.length > 0 && <div className="mb-6"><Notice tone="warn"><p className="font-medium">{t.admin.productionProblems}</p><ul className="mt-1 list-disc pl-5">{q.data.production_problems.map((p) => <li key={p}>{p}</li>)}</ul></Notice></div>}
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title={t.admin.platform}>
          <div className="space-y-4">
            <Field label={t.admin.name}>{(id) => <Input id={id} value={s("platform.name")} onChange={(e) => set("platform.name", e.target.value)} />}</Field>
            <TInput label="Tagline" value={tr("platform.tagline")} onChange={(x) => set("platform.tagline", x)} />
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label={t.dash.language}>{(id) => <Select id={id} value={s("platform.default_language")} onChange={(e) => set("platform.default_language", e.target.value)}><option>uz</option><option>en</option><option>ru</option></Select>}</Field>
              <Field label={t.admin.currency}>{(id) => <Select id={id} value={s("platform.default_currency")} onChange={(e) => set("platform.default_currency", e.target.value)}><option>UZS</option><option>USD</option></Select>}</Field>
              <Field label={t.dash.timezone}>{(id) => <Input id={id} value={s("platform.timezone")} onChange={(e) => set("platform.timezone", e.target.value)} />}</Field>
              <Field label="Contact email">{(id) => <Input id={id} type="email" value={s("platform.contact_email")} onChange={(e) => set("platform.contact_email", e.target.value)} />}</Field>
              <Field label="Contact Telegram">{(id) => <Input id={id} value={s("platform.contact_telegram")} onChange={(e) => set("platform.contact_telegram", e.target.value)} />}</Field>
              <Field label="Upload limit (MB)">{(id) => <Input id={id} type="number" min={1} value={s("uploads.max_mb")} onChange={(e) => set("uploads.max_mb", Number(e.target.value))} />}</Field>
            </div>
            <Field label="File retention (days)">{(id) => <Input id={id} type="number" min={1} value={s("files.retention_days")} onChange={(e) => set("files.retention_days", Number(e.target.value))} />}</Field>
            <Switch label={t.admin.registration} checked={b("auth.registration_enabled")} onCheckedChange={(x) => set("auth.registration_enabled", x)} />
            <Switch label={t.admin.maintenanceMode} checked={b("platform.maintenance_mode")} onCheckedChange={(x) => set("platform.maintenance_mode", x)} />
            {b("platform.maintenance_mode") && <TInput label={t.pages.maintenance} value={tr("platform.maintenance_message")} onChange={(x) => set("platform.maintenance_message", x)} />}
          </div>
        </Panel>
        <div className="space-y-6">
          <Panel title={t.admin.payment}>
            <Field label={t.admin.releasePolicy}>{(id) => <Select id={id} value={s("orders.release_policy")} onChange={(e) => set("orders.release_policy", e.target.value)}><option value="AFTER_FULL_PAYMENT">{t.admin.afterFull}</option><option value="ON_APPROVAL">{t.admin.onApproval}</option></Select>}</Field>
            <Field label="Auto-close after delivery (days)" className="mt-3">{(id) => <Input id={id} type="number" min={1} value={s("orders.auto_close_days")} onChange={(e) => set("orders.auto_close_days", Number(e.target.value))} />}</Field>
            <div className="mt-3"><Switch label={t.admin.manualPayments} checked={b("payments.manual_enabled")} onCheckedChange={(x) => set("payments.manual_enabled", x)} /></div>
            {b("payments.manual_enabled") && <div className="mt-2"><TInput label={t.admin.manualInstr} value={tr("payments.manual_instructions")} onChange={(x) => set("payments.manual_instructions", x)} multiline /></div>}
            <p className="mt-4 text-[13px] text-muted">Click / Payme / Stripe credentials are set in the server environment (.env), never in the browser.</p>
          </Panel>
          <Panel title={t.admin.integrations}>
            <ul className="mb-4 space-y-1.5 text-[14px]">{Object.entries(q.data.integrations).map(([k, ok]) => <li key={k} className="flex justify-between"><span className="capitalize">{k}</span><span className={ok ? "text-ok" : "text-muted"}>{ok ? "OK" : t.common.configRequired}</span></li>)}</ul>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => test("/admin/email/test")}>{t.admin.testEmail}</Button>
              <Button size="sm" variant="outline" onClick={() => test("/admin/telegram/test")}>{t.admin.testTelegram}</Button>
              {me?.permissions.includes("secrets.manage") && <Button size="sm" variant="outline" onClick={() => test("/admin/telegram/setup-webhook")}>{t.admin.setupWebhook}</Button>}
            </div>
          </Panel>
          <Panel title={t.admin.telegramEvents}>
            <Switch label={`Email ${t.dash.notifications.toLowerCase()}`} checked={b("notifications.email_enabled")} onCheckedChange={(x) => set("notifications.email_enabled", x)} />
            <div className="mt-2 grid gap-x-6 sm:grid-cols-2">
              {ADMIN_EVENTS.map((e) => <Switch key={e} label={<code className="text-[12.5px]">{e}</code>} checked={events.includes(e)} onCheckedChange={(x) => set("notifications.telegram_admin_events", x ? [...events, e] : events.filter((y) => y !== e))} />)}
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}
