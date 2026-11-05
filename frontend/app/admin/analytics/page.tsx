"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Money } from "@/components/domain";
import { Input, Select } from "@/components/ui/field";
import { ErrorState, LoadingRows, Notice, PageHeader, Panel, Stat } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";

type A = { orders: { date: string; count: number }[]; revenue: { date: string; currency: string; amount_minor: number }[]; popular_services: { slug: string; name: string; orders: number }[];
  orders_total: number; cancellation_rate: number | null; avg_completion_hours: number | null; outstanding: { currency: string; amount_minor: number }[];
  ai: { success_rate: number | null; fallback_rate: number | null; cost_usd: string; cost_per_ai_order_usd: string | null }; profit_note: string };

const axis = { stroke: "var(--muted)", fontSize: 12, tickLine: false, axisLine: false } as const;
const tip = { contentStyle: { background: "var(--raised)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--fg)" } };

export default function Analytics() {
  const { t } = useI18n();
  const [g, setG] = useState("day");
  const [ccy, setCcy] = useState("UZS");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const range = `${from ? `&date_from=${new Date(from).toISOString()}` : ""}${to ? `&date_to=${new Date(to).toISOString()}` : ""}`;
  const q = useQuery({ queryKey: ["analytics", g, ccy, range], queryFn: () => api<A>(`/admin/analytics?granularity=${g}&currency=${ccy}${range}`) });
  const pct = (v: number | null) => (v === null ? "—" : `${Math.round(v * 100)}%`);
  return (
    <>
      <PageHeader title={t.admin.analytics} />
      <div className="mb-6 flex flex-wrap items-end gap-3">
        <label className="text-[13px]">{t.admin.granularity}<Select value={g} onChange={(e) => setG(e.target.value)} className="mt-1 w-36"><option value="day">{t.admin.day}</option><option value="week">{t.admin.week}</option><option value="month">{t.admin.month}</option></Select></label>
        <label className="text-[13px]">{t.admin.currency}<Select value={ccy} onChange={(e) => setCcy(e.target.value)} className="mt-1 w-28"><option>UZS</option><option>USD</option></Select></label>
        <label className="text-[13px]">{t.common.from}<Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="mt-1" /></label>
        <label className="text-[13px]">—<Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="mt-1" /></label>
      </div>
      {q.isLoading ? <LoadingRows rows={6} /> : q.error || !q.data ? <ErrorState message={errorMessage(q.error, t)} /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label={t.admin.totalOrders} value={q.data.orders_total} />
            <Stat label={t.admin.cancellationRate} value={pct(q.data.cancellation_rate)} />
            <Stat label={t.admin.avgCompletion} value={q.data.avg_completion_hours !== null ? t.admin.hours.replace("{n}", String(q.data.avg_completion_hours)) : "—"} />
            <Stat label={t.admin.successRate} value={pct(q.data.ai.success_rate)} sub={`${t.admin.fallbackRate}: ${pct(q.data.ai.fallback_rate)}`} />
            <Stat label={t.admin.costPerOrder} value={q.data.ai.cost_per_ai_order_usd ? `$${q.data.ai.cost_per_ai_order_usd}` : "—"} sub={`Σ $${q.data.ai.cost_usd}`} />
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <Panel title={t.admin.ordersChart}>
              {q.data.orders.length ? (
                <div className="h-64" role="img" aria-label={t.admin.ordersChart}>
                  <ResponsiveContainer><BarChart data={q.data.orders}><CartesianGrid stroke="var(--border)" vertical={false} /><XAxis dataKey="date" {...axis} /><YAxis allowDecimals={false} {...axis} width={32} /><Tooltip {...tip} cursor={{ fill: "var(--raised)" }} /><Bar dataKey="count" fill="var(--accent)" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer>
                </div>
              ) : <p className="text-muted">{t.common.empty}</p>}
            </Panel>
            <Panel title={`${t.admin.revenueChart} · ${ccy}`}>
              {q.data.revenue.length ? (
                <div className="h-64" role="img" aria-label={t.admin.revenueChart}>
                  <ResponsiveContainer><LineChart data={q.data.revenue.map((r) => ({ date: r.date, amount: r.amount_minor / 100 }))}><CartesianGrid stroke="var(--border)" vertical={false} /><XAxis dataKey="date" {...axis} /><YAxis {...axis} width={70} /><Tooltip {...tip} /><Line type="monotone" dataKey="amount" stroke="var(--accent)" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
                </div>
              ) : <p className="text-muted">{t.common.empty}</p>}
            </Panel>
            <Panel title={t.admin.popular}>
              {q.data.popular_services.length ? <ul className="space-y-2 text-[14px]">{q.data.popular_services.map((s) => {
                const max = q.data.popular_services[0]!.orders;
                return <li key={s.slug}><div className="flex justify-between"><span>{s.name}</span><span className="tabular-nums">{s.orders}</span></div><div className="mt-1 h-1.5 rounded-full bg-raised"><div className="h-full rounded-full bg-accent" style={{ width: `${(s.orders / max) * 100}%` }} /></div></li>;
              })}</ul> : <p className="text-muted">{t.common.empty}</p>}
            </Panel>
            <Panel title={t.admin.outstanding}>
              {q.data.outstanding.length ? q.data.outstanding.map((o) => <p key={o.currency} className="text-[20px] font-semibold"><Money minor={o.amount_minor} currency={o.currency} /></p>) : <p className="text-muted">—</p>}
              <div className="mt-4"><Notice>{q.data.profit_note}</Notice></div>
            </Panel>
          </div>
        </>
      )}
    </>
  );
}
