"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Input, Select } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingRows, PageHeader, Pager } from "@/components/ui/misc";
import { OrderRows } from "@/features/order-list";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { OrderSummary, Paged } from "@/types/api";

export default function AdminOrdersPage() {
  return <Suspense><AdminOrders /></Suspense>;
}

function AdminOrders() {
  const { t } = useI18n();
  const sp = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(sp.get("q") ?? "");
  const status = sp.get("status") ?? "";
  const pay = sp.get("payment_status") ?? "";
  const needs = sp.get("needs_action") === "1";
  const page = Number(sp.get("page") ?? 1);
  const set = (patch: Record<string, string>) => {
    const p = new URLSearchParams(sp.toString());
    Object.entries(patch).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k)));
    if (!("page" in patch)) p.delete("page");
    router.replace(`/admin/orders?${p}`);
  };
  const qs = new URLSearchParams({ page: String(page), page_size: "25" });
  if (sp.get("q")) qs.set("q", sp.get("q")!);
  if (status) qs.set("status", status);
  if (pay) qs.set("payment_status", pay);
  if (needs) qs.set("needs_action", "true");
  if (sp.get("customer_id")) qs.set("customer_id", sp.get("customer_id")!);
  if (sp.get("service_id")) qs.set("service_id", sp.get("service_id")!);
  const data = useQuery({ queryKey: ["admin-orders", qs.toString()], queryFn: () => api<Paged<OrderSummary>>(`/admin/orders?${qs}`) });
  return (
    <>
      <PageHeader title={t.admin.orders} />
      <div className="mb-5 grid gap-3 sm:grid-cols-[1fr_200px_180px_auto]">
        <form onSubmit={(e) => { e.preventDefault(); set({ q }); }}><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.admin.searchOrders} aria-label={t.common.search} /></form>
        <Select value={status} onChange={(e) => set({ status: e.target.value })} aria-label={t.common.status}>
          <option value="">{t.common.all}</option>
          {Object.entries(t.status).map(([k, v]) => <option key={k} value={k}>{v} ({k})</option>)}
        </Select>
        <Select value={pay} onChange={(e) => set({ payment_status: e.target.value })} aria-label={t.admin.payment}>
          <option value="">{t.admin.payment}: {t.common.all}</option>
          {["UNPAID", "DEPOSIT_PAID", "PAID", "PARTIALLY_REFUNDED", "REFUNDED"].map((s) => <option key={s}>{s}</option>)}
        </Select>
        <label className="flex items-center gap-2 text-[14px]"><input type="checkbox" checked={needs} onChange={(e) => set({ needs_action: e.target.checked ? "1" : "" })} className="accent-[var(--accent)]" />{t.admin.needsAction}</label>
      </div>
      {data.isLoading ? <LoadingRows /> : data.error ? <ErrorState message={errorMessage(data.error, t)} />
        : data.data?.items.length ? <><OrderRows items={data.data.items} base="/admin/orders" staff /><Pager page={page} total={data.data.total} size={25} onPage={(p) => set({ page: String(p) })} /></>
        : <EmptyState title={t.common.empty} />}
    </>
  );
}
