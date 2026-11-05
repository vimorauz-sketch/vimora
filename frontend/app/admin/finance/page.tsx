"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/field";
import { Dialog, ErrorState, LoadingRows, Notice, PageHeader, Panel, Stat, Table, Tabs, TabsContent, TabsList } from "@/components/ui/misc";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Payment } from "@/types/api";

type Summary = { currencies: Record<string, { gross_minor: number; deposits_minor: number; final_minor: number; full_minor: number; payments: number; refunded_minor: number; outstanding_minor: number; net_minor: number }>;
  ai_expenses_usd: string; net_estimate_note: string; by_service: { service: string; currency: string; amount_minor: number }[] };
type Refund = { id: number; order_id: number; order_number: string; payment_id: number; amount_minor: number; currency: string; status: string; reason: string; provider_refund_id: string | null; created_at: string };

const iso = (d: string) => (d ? new Date(d).toISOString() : "");

export default function Finance() {
  const { t, locale } = useI18n();
  const { data: me } = useMe();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [status, setStatus] = useState("");
  const range = `${from ? `&date_from=${iso(from)}` : ""}${to ? `&date_to=${iso(to)}` : ""}`;
  const sum = useQuery({ queryKey: ["fin-sum", range], queryFn: () => api<Summary>(`/admin/finance/summary?x=1${range}`) });
  const pays = useQuery({ queryKey: ["fin-pay", status], queryFn: () => api<{ items: Payment[] }>(`/admin/finance/payments?page_size=100${status ? `&status=${status}` : ""}`) });
  const refunds = useQuery({ queryKey: ["fin-ref"], queryFn: () => api<{ items: Refund[] }>("/admin/finance/refunds") });
  const recon = useQuery({ queryKey: ["fin-recon"], queryFn: () => api<{ stale_processing: Payment[]; amount_mismatches: unknown[]; ledger_drift: unknown[] }>("/admin/finance/reconciliation") });
  const [complete, setComplete] = useState<Refund | null>(null);
  const [refId, setRefId] = useState("");
  return (
    <>
      <PageHeader title={t.admin.finance} actions={<Button asChild variant="outline"><a href={`/api/v1/admin/finance/export.csv?x=1${range}`}>{t.admin.exportCsv}</a></Button>} />
      <div className="mb-6 flex flex-wrap items-end gap-3">
        <label className="text-[13px]">{t.common.from}<Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="mt-1" /></label>
        <label className="text-[13px]">—<Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="mt-1" /></label>
      </div>
      {sum.isLoading ? <LoadingRows /> : sum.error || !sum.data ? <ErrorState message={errorMessage(sum.error, t)} /> : (
        <>
          {Object.keys(sum.data.currencies).length === 0 && <p className="text-muted">{t.common.empty}</p>}
          {Object.entries(sum.data.currencies).map(([ccy, m]) => (
            <div key={ccy} className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <Stat label={`${t.admin.gross} · ${ccy}`} value={<Money minor={m.gross_minor} currency={ccy} />} sub={`${m.payments}`} />
              <Stat label={t.admin.deposits} value={<Money minor={m.deposits_minor} currency={ccy} />} />
              <Stat label={t.admin.refunded} value={<Money minor={m.refunded_minor} currency={ccy} />} />
              <Stat label={t.admin.net} value={<Money minor={m.net_minor} currency={ccy} />} accent />
              <Stat label={t.admin.outstanding} value={<Money minor={m.outstanding_minor} currency={ccy} />} />
            </div>
          ))}
          <div className="grid gap-4 sm:grid-cols-[240px_1fr]">
            <Stat label={t.admin.aiExpenses} value={`$${sum.data.ai_expenses_usd}`} />
            <Notice>{sum.data.net_estimate_note}</Notice>
          </div>
        </>
      )}
      <Tabs defaultValue="payments" className="mt-10">
        <TabsList items={[{ value: "payments", label: t.dash.payments }, { value: "refunds", label: t.admin.refund }, { value: "services", label: t.admin.byService }, { value: "recon", label: t.admin.reconciliation }]} />
        <TabsContent value="payments">
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="mb-4 max-w-[220px]" aria-label={t.common.status}>
            <option value="">{t.common.all}</option>{["PENDING", "PROCESSING", "SUCCEEDED", "FAILED", "CANCELLED", "REFUNDED"].map((s) => <option key={s}>{s}</option>)}
          </Select>
          <Table head={[t.common.date, t.dash.order, t.admin.customer, t.admin.payment, t.common.amount, t.common.status]}>
            {pays.data?.items.map((p) => (
              <tr key={p.id}>
                <td className="px-4 py-3">{date(p.created_at, locale, true)}</td>
                <td className="px-4 py-3"><Link href={`/admin/orders/${p.order_id}`} className="hover:underline">#{p.order_number}</Link></td>
                <td className="px-4 py-3 text-[13px]">{p.customer_email}</td>
                <td className="px-4 py-3 text-[13px]">{p.provider} · {p.kind}<span className="block text-muted">{p.provider_transaction_id}</span></td>
                <td className="px-4 py-3"><Money minor={p.amount_minor} currency={p.currency} /></td>
                <td className={`px-4 py-3 ${p.status === "SUCCEEDED" ? "text-ok" : ""}`}>{p.status}</td>
              </tr>
            ))}
          </Table>
        </TabsContent>
        <TabsContent value="refunds">
          <Table head={[t.dash.order, t.common.amount, t.admin.reason, t.common.status, ""]}>
            {refunds.data?.items.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-3"><Link href={`/admin/orders/${r.order_id}`} className="hover:underline">#{r.order_number}</Link></td>
                <td className="px-4 py-3"><Money minor={r.amount_minor} currency={r.currency} /></td>
                <td className="px-4 py-3 text-[13px]">{r.reason}</td>
                <td className="px-4 py-3">{r.status}{r.provider_refund_id && <span className="block text-[12px] text-muted">{r.provider_refund_id}</span>}</td>
                <td className="px-4 py-3">{me?.permissions.includes("finance.manage") && ["REQUESTED", "APPROVED"].includes(r.status) && <Button size="sm" variant="outline" onClick={() => setComplete(r)}>{t.admin.completeRefund}</Button>}</td>
              </tr>
            ))}
          </Table>
        </TabsContent>
        <TabsContent value="services">
          <Panel>{sum.data?.by_service.length ? <ul className="divide-y divide-border text-[14px]">{sum.data.by_service.map((b, i) => <li key={i} className="flex justify-between py-2"><span>{b.service}</span><Money minor={b.amount_minor} currency={b.currency} /></li>)}</ul> : <p className="text-muted">{t.common.empty}</p>}</Panel>
        </TabsContent>
        <TabsContent value="recon">
          <Panel>
            <p className="text-[14px]">Stale processing: {recon.data?.stale_processing.length ?? "—"} · Amount mismatches: {recon.data?.amount_mismatches.length ?? "—"} · Ledger drift: {recon.data?.ledger_drift.length ?? "—"}</p>
            <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-[12px] text-muted">{JSON.stringify(recon.data, null, 2)}</pre>
          </Panel>
        </TabsContent>
      </Tabs>
      <Dialog open={!!complete} onOpenChange={(o) => !o && setComplete(null)} title={t.admin.completeRefund}
        footer={<Button onClick={async () => { try { await api(`/admin/orders/${complete!.order_id}/refunds/${complete!.id}/complete`, { body: { provider_refund_id: refId } }); setComplete(null); setRefId(""); void refunds.refetch(); void sum.refetch(); } catch (e) { toast.error(errorMessage(e, t)); } }} disabled={!refId}>{t.common.confirm}</Button>}>
        <p className="mb-3 text-[13.5px] text-muted">Execute the refund in the Click/Payme merchant cabinet first and enter its ID here. For Stripe, enter “auto” to refund through the Stripe API.</p>
        <Input aria-label={t.admin.providerRefId} placeholder={t.admin.providerRefId} value={refId} onChange={(e) => setRefId(e.target.value)} />
      </Dialog>
    </>
  );
}
