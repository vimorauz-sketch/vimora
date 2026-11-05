"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Money, StatusBadge } from "@/components/domain";
import { ErrorState, LoadingRows, PageHeader, Panel, Stat } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";

type Overview = {
  customers: number; orders_total: number; orders_new_24h: number; awaiting_review: number; processing: number; completed: number; cancelled: number; ready_for_delivery: number;
  ai_jobs_running: number; ai_failures_7d: number; ai_spent_today_usd: string; integrations: Record<string, boolean>;
  finance?: { by_currency: Record<string, { revenue_minor: number; deposits_minor: number; outstanding_minor: number; refunded_minor: number }>; ai_expenses_total_usd: string };
  recent_orders: { id: number; order_number: string; title: string; status: string; customer_email: string; created_at: string; total_minor: number; currency: string }[];
};

export default function AdminOverview() {
  const { t, locale } = useI18n();
  const q = useQuery({ queryKey: ["admin-overview"], queryFn: () => api<Overview>("/admin/overview"), refetchInterval: 30_000 });
  if (q.isLoading) return <LoadingRows rows={6} />;
  if (q.error || !q.data) return <ErrorState message={errorMessage(q.error, t)} onRetry={() => q.refetch()} />;
  const d = q.data;
  return (
    <>
      <PageHeader title={t.admin.overview} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link href="/admin/orders?needs_action=1"><Stat label={t.admin.awaitingReview} value={d.awaiting_review} accent={d.awaiting_review > 0} /></Link>
        <Link href="/admin/orders?status=READY_FOR_DELIVERY"><Stat label={t.admin.readyDelivery} value={d.ready_for_delivery} accent={d.ready_for_delivery > 0} /></Link>
        <Stat label={t.admin.processing} value={d.processing} />
        <Stat label={t.admin.newOrders} value={d.orders_new_24h} />
        <Stat label={t.admin.totalOrders} value={d.orders_total} />
        <Stat label={t.admin.completed} value={d.completed} />
        <Stat label={t.admin.cancelled} value={d.cancelled} />
        <Stat label={t.admin.customersCount} value={d.customers} />
        <Stat label={t.admin.aiRunning} value={d.ai_jobs_running} />
        <Stat label={t.admin.aiFailures} value={d.ai_failures_7d} accent={d.ai_failures_7d > 0} />
        <Stat label={t.admin.aiSpendToday} value={`$${d.ai_spent_today_usd}`} />
        {d.finance && <Stat label={t.admin.aiTotal} value={`$${d.finance.ai_expenses_total_usd}`} />}
      </div>
      {d.finance && Object.keys(d.finance.by_currency).length > 0 && (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {Object.entries(d.finance.by_currency).map(([ccy, m]) => (
            <Panel key={ccy} title={`${t.admin.revenue} · ${ccy}`}>
              <dl className="grid grid-cols-2 gap-4 text-[14px]">
                <div><dt className="text-muted">{t.admin.revenue}</dt><dd className="text-[18px] font-semibold"><Money minor={m.revenue_minor} currency={ccy} /></dd></div>
                <div><dt className="text-muted">{t.admin.deposits}</dt><dd className="text-[18px]"><Money minor={m.deposits_minor} currency={ccy} /></dd></div>
                <div><dt className="text-muted">{t.admin.outstanding}</dt><dd className="text-[18px]"><Money minor={m.outstanding_minor} currency={ccy} /></dd></div>
                <div><dt className="text-muted">{t.admin.refunded}</dt><dd className="text-[18px]"><Money minor={m.refunded_minor} currency={ccy} /></dd></div>
              </dl>
            </Panel>
          ))}
        </div>
      )}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Panel title={t.admin.recentOrders}>
          {d.recent_orders.length === 0 ? <p className="text-muted">{t.common.empty}</p> : (
            <ul className="divide-y divide-border text-[14px]">
              {d.recent_orders.map((o) => (
                <li key={o.id}><Link href={`/admin/orders/${o.id}`} className="flex flex-wrap items-center justify-between gap-3 py-3 hover:text-accent">
                  <span className="min-w-0"><span className="tabular-nums text-muted">#{o.order_number}</span> {o.title}<span className="block text-[12.5px] text-muted">{o.customer_email} · {date(o.created_at, locale, true)}</span></span>
                  <StatusBadge status={o.status} staff />
                </Link></li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title={t.admin.integrations}>
          <ul className="space-y-2 text-[14px]">
            {Object.entries(d.integrations).map(([k, v]) => (
              <li key={k} className="flex justify-between"><span className="capitalize">{k}</span><span className={v ? "text-ok" : "text-muted"}>{v ? "OK" : t.common.configRequired}</span></li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}
