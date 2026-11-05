"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { ErrorState, LoadingRows, PageHeader, Panel, Stat, Switch, Table } from "@/components/ui/misc";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Execution } from "@/types/api";

type Overview = {
  enabled: boolean; configured: boolean; env_provider_configured: boolean; spent_today_usd: string; daily_budget_usd: string; per_execution_budget_usd: string; max_retries: number;
  max_executions_per_day: number; executions_today: number; tokens_today: { input: number; output: number }; by_status: Record<string, number>;
  last_30_days: { finished: number; success_rate: number | null; fallback_rate: number | null }; sandbox_enabled: boolean;
};
type Provider = { id: number; key: string; display_name: string; base_url: string | null; has_api_key: boolean; api_key_hint: string | null; is_enabled: boolean; last_health_ok: boolean | null; last_error: string | null };
type Model = { id: number; provider_id: number; purpose: string; model_identifier: string; input_cost_per_mtok: string; output_cost_per_mtok: string; max_tokens: number; is_active: boolean };

const pct = (v: number | null) => (v === null ? "—" : `${Math.round(v * 100)}%`);

export default function AIControl() {
  const { t, locale } = useI18n();
  const { data: me } = useMe();
  const canConfigure = !!me?.permissions.includes("ai.configure");
  const ov = useQuery({ queryKey: ["ai-ov"], queryFn: () => api<Overview>("/admin/ai/overview"), refetchInterval: 20_000 });
  const ex = useQuery({ queryKey: ["ai-ex"], queryFn: () => api<{ items: Execution[] }>("/admin/ai/executions"), refetchInterval: 20_000 });
  const prov = useQuery({ queryKey: ["ai-prov"], queryFn: () => api<{ providers: Provider[]; models: Model[] }>("/admin/ai/providers"), enabled: canConfigure });
  if (ov.isLoading) return <LoadingRows rows={6} />;
  if (ov.error || !ov.data) return <ErrorState message={errorMessage(ov.error, t)} />;
  const o = ov.data;
  async function setSetting(key: string, value: unknown) {
    try { await api("/admin/settings", { method: "PATCH", body: { values: { [key]: value } } }); void ov.refetch(); toast.success(t.common.saved); } catch (e) { toast.error(errorMessage(e, t)); }
  }
  return (
    <>
      <PageHeader title={t.admin.ai} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label={t.admin.spent} value={`$${o.spent_today_usd}`} sub={`/ $${o.daily_budget_usd}`} />
        <Stat label={t.admin.maxPerDay} value={`${o.executions_today} / ${o.max_executions_per_day}`} />
        <Stat label={t.admin.successRate} value={pct(o.last_30_days.success_rate)} sub="30d" />
        <Stat label={t.admin.fallbackRate} value={pct(o.last_30_days.fallback_rate)} sub="30d" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel title={t.admin.settings}>
          <Switch label={t.admin.aiEnabled} checked={o.enabled} disabled={!canConfigure} onCheckedChange={(v) => setSetting("ai.enabled", v)} />
          {!o.configured && <p className="mt-2 text-[13px] text-warn">{t.admin.aiDisabled}</p>}
          {canConfigure && <BudgetForm o={o} onSave={setSetting} />}
          <p className="mt-4 text-[13px] text-muted">Sandbox: {o.sandbox_enabled ? "on" : t.common.configRequired} · tokens today {o.tokens_today.input.toLocaleString()} / {o.tokens_today.output.toLocaleString()}</p>
        </Panel>
        {canConfigure && prov.data && <ProvidersPanel data={prov.data} onChange={() => { void prov.refetch(); void ov.refetch(); }} />}
      </div>
      <h2 className="mb-4 mt-10 text-[17px] font-semibold">{t.admin.executions}</h2>
      {ex.data && ex.data.items.length > 0 ? (
        <Table head={["ID", t.dash.order, t.admin.capability, t.common.status, t.admin.tokens, t.admin.cost, t.common.date]}>
          {ex.data.items.map((e) => (
            <tr key={e.id} className="hover:bg-surface">
              <td className="px-4 py-3"><Link className="underline-offset-4 hover:underline" href={`/admin/ai/${e.id}`}>#{e.id}</Link></td>
              <td className="px-4 py-3"><Link className="hover:underline" href={`/admin/orders/${e.order_id}`}>#{e.order_number}</Link></td>
              <td className="px-4 py-3">{e.capability ?? "—"}</td>
              <td className={`px-4 py-3 ${e.status === "REVIEW_REQUIRED" ? "text-accent" : e.status === "FAILED" ? "text-danger" : ""}`}>{e.status}</td>
              <td className="px-4 py-3 tabular-nums">{e.input_tokens + e.output_tokens}</td>
              <td className="px-4 py-3 tabular-nums">${Number(e.cost_usd).toFixed(4)}</td>
              <td className="px-4 py-3">{date(e.created_at, locale, true)}</td>
            </tr>
          ))}
        </Table>
      ) : <p className="text-muted">{t.common.empty}</p>}
    </>
  );
}

function BudgetForm({ o, onSave }: { o: Overview; onSave: (k: string, v: unknown) => void }) {
  const { t } = useI18n();
  const [v, setV] = useState({ daily: o.daily_budget_usd, per: o.per_execution_budget_usd, retries: o.max_retries, perDay: o.max_executions_per_day });
  return (
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      <Field label={t.admin.dailyBudget}>{(id) => <Input id={id} inputMode="decimal" value={v.daily} onChange={(e) => setV({ ...v, daily: e.target.value })} onBlur={() => onSave("ai.daily_budget_usd", v.daily)} />}</Field>
      <Field label={t.admin.perExecBudget}>{(id) => <Input id={id} inputMode="decimal" value={v.per} onChange={(e) => setV({ ...v, per: e.target.value })} onBlur={() => onSave("ai.per_execution_budget_usd", v.per)} />}</Field>
      <Field label={t.admin.maxRetries}>{(id) => <Input id={id} type="number" min={0} max={10} value={v.retries} onChange={(e) => setV({ ...v, retries: Number(e.target.value) })} onBlur={() => onSave("ai.max_retries", v.retries)} />}</Field>
      <Field label={t.admin.maxPerDay}>{(id) => <Input id={id} type="number" min={0} value={v.perDay} onChange={(e) => setV({ ...v, perDay: Number(e.target.value) })} onBlur={() => onSave("ai.max_executions_per_day", v.perDay)} />}</Field>
    </div>
  );
}

function ProvidersPanel({ data, onChange }: { data: { providers: Provider[]; models: Model[] }; onChange: () => void }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ key: "anthropic", display_name: "Anthropic", base_url: "", api_key: "", is_enabled: true });
  const [model, setModel] = useState({ provider_id: data.providers[0]?.id ?? 0, purpose: "default", model_identifier: "", input_cost_per_mtok: 0, output_cost_per_mtok: 0, max_tokens: 4096, temperature: 0.2, is_active: true });
  const run = async (fn: () => Promise<unknown>) => { try { await fn(); onChange(); toast.success(t.common.saved); } catch (e) { toast.error(errorMessage(e, t)); } };
  return (
    <Panel title={t.admin.providers}>
      <ul className="mb-4 space-y-3 text-[14px]">
        {data.providers.map((p) => (
          <li key={p.id} className="rounded-[8px] border border-border p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{p.display_name} <span className="text-muted">({p.key})</span></span>
              <span className={p.is_enabled ? "text-ok" : "text-muted"}>{p.is_enabled ? t.admin.active : "off"}</span>
            </div>
            <p className="text-[12.5px] text-muted">{p.has_api_key ? t.admin.apiKeySet.replace("{hint}", p.api_key_hint ?? "") : t.admin.apiKeyNone}{p.last_health_ok === false && ` · ${p.last_error}`}</p>
            <Button size="sm" variant="ghost" className="mt-1" onClick={() => run(async () => { const r = await api<{ ok: boolean; error?: string }>(`/admin/ai/providers/${p.id}/test`, { method: "POST" }); if (!r.ok) throw new Error(r.error); })}>{t.admin.test}</Button>
            <ul className="mt-2 space-y-1 text-[13px]">
              {data.models.filter((m) => m.provider_id === p.id).map((m) => (
                <li key={m.id} className="flex justify-between"><span>{m.purpose}: <code>{m.model_identifier}</code></span><button className="text-muted hover:text-danger" onClick={() => run(() => api(`/admin/ai/models/${m.id}`, { method: "DELETE" }))}>{t.common.delete}</button></li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      <details className="rounded-[8px] border border-border p-3">
        <summary className="cursor-pointer text-[14px] font-medium">{t.admin.providers} +</summary>
        <div className="mt-3 grid gap-3">
          <Select aria-label="provider" value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })}><option>anthropic</option><option>openai</option><option>openai_compatible</option></Select>
          <Input aria-label={t.admin.name} value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          <Input aria-label={t.admin.baseUrl} placeholder={`${t.admin.baseUrl} (https://…)`} value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
          <Input aria-label={t.admin.apiKey} type="password" autoComplete="off" placeholder={t.admin.apiKey} value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
          <Switch label={t.admin.active} checked={form.is_enabled} onCheckedChange={(v) => setForm({ ...form, is_enabled: v })} />
          <Button size="sm" onClick={() => run(() => api("/admin/ai/providers", { body: { ...form, base_url: form.base_url || null, api_key: form.api_key || null } }).then(() => setForm({ ...form, api_key: "" })))}>{t.common.save}</Button>
        </div>
      </details>
      {data.providers.length > 0 && (
        <details className="mt-3 rounded-[8px] border border-border p-3">
          <summary className="cursor-pointer text-[14px] font-medium">{t.admin.addModel}</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Select aria-label="provider" value={model.provider_id} onChange={(e) => setModel({ ...model, provider_id: Number(e.target.value) })}>{data.providers.map((p) => <option key={p.id} value={p.id}>{p.display_name}</option>)}</Select>
            <Select aria-label={t.admin.purpose} value={model.purpose} onChange={(e) => setModel({ ...model, purpose: e.target.value })}>{["default", "router", "planner", "executor", "validator", "assistant"].map((p) => <option key={p}>{p}</option>)}</Select>
            <Input className="sm:col-span-2" aria-label={t.admin.modelId} placeholder={t.admin.modelId} value={model.model_identifier} onChange={(e) => setModel({ ...model, model_identifier: e.target.value })} />
            <Field label={t.admin.inCost}>{(id) => <Input id={id} type="number" step="0.01" min={0} value={model.input_cost_per_mtok} onChange={(e) => setModel({ ...model, input_cost_per_mtok: Number(e.target.value) })} />}</Field>
            <Field label={t.admin.outCost}>{(id) => <Input id={id} type="number" step="0.01" min={0} value={model.output_cost_per_mtok} onChange={(e) => setModel({ ...model, output_cost_per_mtok: Number(e.target.value) })} />}</Field>
            <Button size="sm" onClick={() => run(() => api("/admin/ai/models", { body: model }))}>{t.common.create}</Button>
          </div>
          <p className="mt-2 text-[12px] text-muted">Enter prices from your provider's current price list so cost tracking and budgets are accurate.</p>
        </details>
      )}
    </Panel>
  );
}
