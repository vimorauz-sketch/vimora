"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { EmptyState, ErrorState, LoadingRows, PageHeader, Pager } from "@/components/ui/misc";
import { OrderRows } from "@/features/order-list";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { OrderSummary, Paged } from "@/types/api";

const STAGES = ["new", "awaiting_quote", "awaiting_payment", "in_progress", "ready", "arranging", "completed", "cancelled"] as const;

export default function LocalOrdersPage() {
  return <Suspense><LocalOrders /></Suspense>;
}

function LocalOrders() {
  const { t } = useI18n();
  const L = t.biz.adminLocal;
  const sp = useSearchParams();
  const router = useRouter();
  const stage = sp.get("stage") ?? "";
  const method = sp.get("method") ?? "";
  const page = Number(sp.get("page") ?? 1);
  const set = (patch: Record<string, string>) => {
    const p = new URLSearchParams(sp.toString());
    Object.entries(patch).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k)));
    if (!("page" in patch)) p.delete("page");
    router.replace(`/admin/local-orders?${p}`);
  };
  const summary = useQuery({ queryKey: ["local-summary"], queryFn: () => api<Record<string, number>>("/admin/orders/local-summary"), refetchInterval: 30_000 });
  const qs = new URLSearchParams({ local: "true", page: String(page), page_size: "25" });
  if (stage) qs.set("local_stage", stage);
  if (method) qs.set("handover_method", method);
  const data = useQuery({ queryKey: ["admin-local-orders", qs.toString()], queryFn: () => api<Paged<OrderSummary>>(`/admin/orders?${qs}`), refetchInterval: 30_000 });
  return (
    <>
      <PageHeader title={L.title} sub={L.sub} />
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {STAGES.map((s) => (
          <button key={s} type="button" onClick={() => set({ stage: stage === s ? "" : s })} aria-pressed={stage === s}
            className={cn("card card-hover px-4 py-3 text-left", stage === s && "border-accent ring-1 ring-accent")}>
            <span className="block text-[12.5px] text-muted">{L.stages[s]}</span>
            <span className="mt-1 block text-[24px] font-semibold tabular-nums">{summary.data?.[s] ?? "—"}</span>
          </button>
        ))}
      </div>
      <div className="mb-5 flex flex-wrap gap-1.5" role="group" aria-label={t.biz.handover}>
        {([["", L.all], ["PICKUP", L.pickup], ["MEETUP", L.meetup]] as const).map(([v, label]) => (
          <button key={v || "all"} type="button" onClick={() => set({ method: v })} aria-pressed={method === v}
            className={cn("rounded-full border px-4 py-1.5 text-[13.5px]", method === v ? "border-ink bg-ink text-ink-fg" : "border-border bg-surface hover:border-accent/60")}>{label}</button>
        ))}
      </div>
      {data.isLoading ? <LoadingRows /> : data.error ? <ErrorState message={errorMessage(data.error, t)} onRetry={() => data.refetch()} />
        : data.data?.items.length ? <><OrderRows items={data.data.items} base="/admin/orders" staff /><Pager page={page} total={data.data.total} size={25} onPage={(p) => set({ page: String(p) })} /></>
        : <EmptyState title={t.common.empty} />}
    </>
  );
}
