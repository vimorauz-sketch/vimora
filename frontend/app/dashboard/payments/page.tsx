"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Money } from "@/components/domain";
import { EmptyState, ErrorState, LoadingRows, PageHeader, Table } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Payment } from "@/types/api";

export default function PaymentsPage() {
  const { t, locale } = useI18n();
  const q = useQuery({ queryKey: ["my-payments"], queryFn: () => api<{ items: Payment[] }>("/account/payments") });
  return (
    <>
      <PageHeader title={t.dash.payments} />
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} /> : !q.data?.items.length ? <EmptyState title={t.common.empty} /> : (
        <Table head={[t.common.date, t.dash.order, t.admin.payment, t.common.amount, t.common.status]}>
          {q.data.items.map((p) => (
            <tr key={p.id}>
              <td className="px-4 py-3 tabular-nums">{date(p.created_at, locale, true)}</td>
              <td className="px-4 py-3"><Link className="underline-offset-4 hover:underline" href={`/dashboard/orders/${p.order_id}`}>#{p.order_number}</Link></td>
              <td className="px-4 py-3">{p.provider} <span className="text-muted">· {p.kind}</span></td>
              <td className="px-4 py-3"><Money minor={p.amount_minor} currency={p.currency} /></td>
              <td className={`px-4 py-3 ${p.status === "SUCCEEDED" ? "text-ok" : "text-muted"}`}>{p.status}</td>
            </tr>
          ))}
        </Table>
      )}
    </>
  );
}
