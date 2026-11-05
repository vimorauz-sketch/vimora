"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRows, PageHeader, Pager } from "@/components/ui/misc";
import { OrderRows } from "@/features/order-list";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { OrderSummary, Paged } from "@/types/api";

export default function OrdersPage() {
  const { t, locale } = useI18n();
  const [filter, setFilter] = useState<"active" | "">("active");
  const [page, setPage] = useState(1);
  const q = useQuery({ queryKey: ["orders", filter, page, locale], queryFn: () => api<Paged<OrderSummary>>(`/orders?page=${page}&page_size=20&lang=${locale}${filter ? `&status=${filter}` : ""}`) });
  return (
    <>
      <PageHeader title={t.dash.orders} actions={<Button asChild><Link href="/services">{t.dash.newOrder}</Link></Button>} />
      <div className="mb-5 flex gap-1" role="group">
        {([["active", t.dash.filterActive], ["", t.dash.filterAll]] as const).map(([v, l]) => (
          <button key={v} onClick={() => { setFilter(v); setPage(1); }} aria-pressed={filter === v} className={cn("rounded-[6px] px-3 py-1.5 text-[14px]", filter === v ? "bg-raised" : "text-muted hover:text-fg")}>{l}</button>
        ))}
      </div>
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} onRetry={() => q.refetch()} />
        : q.data?.items.length ? <><OrderRows items={q.data.items} /><Pager page={page} total={q.data.total} size={20} onPage={setPage} /></>
        : <EmptyState title={t.dash.noOrders} action={<Button asChild size="sm"><Link href="/services">{t.dash.browse}</Link></Button>} />}
    </>
  );
}
