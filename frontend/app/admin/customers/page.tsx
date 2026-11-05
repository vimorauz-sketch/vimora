"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Money } from "@/components/domain";
import { Input } from "@/components/ui/field";
import { ErrorState, LoadingRows, PageHeader, Pager, Table } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";

type Row = { id: number; email: string; full_name: string; is_active: boolean; email_verified: boolean; roles: string[]; created_at: string; last_login_at: string | null; order_count: number; paid_minor: number };

export default function Customers() {
  const { t, locale } = useI18n();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [staff, setStaff] = useState(false);
  const [page, setPage] = useState(1);
  const data = useQuery({ queryKey: ["customers", search, staff, page], queryFn: () => api<{ items: Row[]; total: number }>(`/admin/customers?page=${page}&staff_only=${staff}${search ? `&q=${encodeURIComponent(search)}` : ""}`) });
  return (
    <>
      <PageHeader title={t.admin.customers} />
      <div className="mb-5 flex flex-wrap items-center gap-4">
        <form onSubmit={(e) => { e.preventDefault(); setSearch(q); setPage(1); }} className="w-full max-w-sm"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.common.search} aria-label={t.common.search} /></form>
        <label className="flex items-center gap-2 text-[14px]"><input type="checkbox" checked={staff} onChange={(e) => setStaff(e.target.checked)} className="accent-[var(--accent)]" />{t.admin.staffRole}</label>
      </div>
      {data.isLoading ? <LoadingRows /> : data.error ? <ErrorState message={errorMessage(data.error, t)} /> : (
        <>
          <Table head={[t.admin.customer, t.admin.orders, t.common.paid, t.dash.created, t.common.status]}>
            {data.data?.items.map((c) => (
              <tr key={c.id} className="hover:bg-surface">
                <td className="px-4 py-3"><Link href={`/admin/customers/${c.id}`} className="font-medium hover:underline">{c.full_name || "—"}</Link><span className="block text-[12.5px] text-muted">{c.email}{c.roles.filter((r) => r !== "CUSTOMER").map((r) => ` · ${r}`)}</span></td>
                <td className="px-4 py-3 tabular-nums">{c.order_count}</td>
                <td className="px-4 py-3">{c.paid_minor ? <Money minor={c.paid_minor} currency="UZS" /> : "—"}</td>
                <td className="px-4 py-3">{date(c.created_at, locale)}</td>
                <td className="px-4 py-3 text-[13px]">{c.is_active ? (c.email_verified ? <span className="text-ok">✓</span> : <span className="rounded-full bg-tint-5 px-2 py-0.5 text-warn">{t.admin.unverified}</span>) : <span className="text-danger">{t.admin.disabledLabel}</span>}</td>
              </tr>
            ))}
          </Table>
          <Pager page={page} total={data.data?.total ?? 0} size={25} onPage={setPage} />
        </>
      )}
    </>
  );
}
