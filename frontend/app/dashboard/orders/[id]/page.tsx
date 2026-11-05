"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";
import { FileChip, FileUploader, Money, StageRail, StatusBadge } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRows, Notice, Panel, Tabs, TabsContent, TabsList } from "@/components/ui/misc";
import { MessageThread } from "@/features/messages";
import { HandoverPanel, requirementLabel } from "@/features/local/handover";
import { CancelOrder, DeliveredActions, PaymentPanel, PaymentReturnWatcher, QuotationCard } from "@/features/order-actions";
import { Timeline } from "@/features/timeline";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Attachment, OrderDetail } from "@/types/api";

export default function OrderPage() {
  return <Suspense fallback={<LoadingRows />}><OrderView /></Suspense>;
}

function OrderView() {
  const { t, locale } = useI18n();
  const { id } = useParams<{ id: string }>();
  const tab = useSearchParams().get("tab") ?? "summary";
  const q = useQuery({ queryKey: ["order", Number(id)], queryFn: () => api<OrderDetail>(`/orders/${id}?lang=${locale}`), refetchInterval: 30_000 });
  const [extra, setExtra] = useState<Attachment[]>([]);
  if (q.isLoading) return <LoadingRows rows={6} />;
  if (q.error || !q.data) return <ErrorState message={errorMessage(q.error, t)} onRetry={() => q.refetch()} />;
  const o = q.data;
  const refresh = () => void q.refetch();
  const openQuote = o.quotations.find((x) => x.status === "PENDING");
  const accepted = o.quotations.find((x) => x.status === "ACCEPTED");
  return (
    <>
      <div className="mb-8">
        <p className="text-[13px] tabular-nums text-muted">#{o.order_number} · {date(o.created_at, locale)}</p>
        <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
          <h1 className="display text-[26px] sm:text-[32px]">{o.title}</h1>
          <StatusBadge status={o.status} />
        </div>
        <div className="mt-6 max-w-3xl"><StageRail status={o.status} /></div>
      </div>
      <div className="mb-6 space-y-3"><PaymentReturnWatcher orderId={o.id} /></div>
      <Tabs defaultValue={tab}>
        <TabsList items={[{ value: "summary", label: t.dash.tabs.summary }, { value: "messages", label: t.dash.tabs.messages }, { value: "files", label: t.dash.tabs.files }, { value: "payments", label: t.dash.tabs.payments }, { value: "timeline", label: t.dash.tabs.timeline }]} />
        <TabsContent value="summary">
          <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
            <div className="space-y-6">
              {o.ai_assisted && ["DELIVERED", "CLOSED"].includes(o.status) && <Notice>{t.dash.aiNote}</Notice>}
              {o.customer_notes && <Notice>{o.customer_notes}</Notice>}
              <Panel title={t.dash.order}>
                {o.service_name && <p className="mb-2 text-[13px] text-muted">{o.service_name}</p>}
                <p className="whitespace-pre-line">{o.description}</p>
                {Object.keys(o.requirements).length > 0 && (
                  <dl className="mt-4 grid gap-2 border-t border-border pt-4 text-[14px] sm:grid-cols-2">
                    {Object.entries(o.requirements).map(([k, v]) => { const [kl, vl] = requirementLabel(t, k, v); return <div key={k}><dt className="text-muted">{kl}</dt><dd>{vl}</dd></div>; })}
                  </dl>
                )}
              </Panel>
              {["DELIVERED", "CLOSED", "REVISION_REQUESTED"].includes(o.status) && (!o.is_local || o.deliverables.length > 0) && (
                <Panel title={t.dash.delivered}>
                  {o.deliverables.length ? <div className="space-y-2">{o.deliverables.map((d) => d.attachment && <FileChip key={d.id} file={{ ...d.attachment, name: d.title || d.attachment.name }} />)}</div> : <p className="text-muted">{t.dash.noDeliverables}</p>}
                  <div className="mt-5"><DeliveredActions order={o} onDone={refresh} /></div>
                </Panel>
              )}
            </div>
            <div className="space-y-6">
              {o.handover && <HandoverPanel order={o} onDone={refresh} />}
              {openQuote && <QuotationCard order={o} q={openQuote} onDone={refresh} />}
              <PaymentPanel order={o} onDone={refresh} />
              {!openQuote && accepted && (
                <Panel title={t.dash.quotation}>
                  <dl className="space-y-1.5 text-[14px]">
                    <div className="flex justify-between font-semibold"><dt>{t.common.total}</dt><dd><Money minor={o.total_minor} currency={o.currency} /></dd></div>
                    <div className="flex justify-between"><dt className="text-muted">{t.common.paid}</dt><dd><Money minor={o.paid_minor} currency={o.currency} /></dd></div>
                    <div className="flex justify-between"><dt className="text-muted">{t.common.remaining}</dt><dd><Money minor={o.remaining_minor} currency={o.currency} /></dd></div>
                  </dl>
                </Panel>
              )}
              {!openQuote && !accepted && o.quotations.length === 0 && <Notice>{t.services.quoteNote}</Notice>}
              <CancelOrder order={o} onDone={refresh} />
            </div>
          </div>
        </TabsContent>
        <TabsContent value="messages"><Panel><MessageThread orderId={o.id} /></Panel></TabsContent>
        <TabsContent value="files">
          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title={t.dash.yourFiles}>
              {o.attachments.length ? <div className="space-y-2">{o.attachments.map((a) => <FileChip key={a.id} file={a} />)}</div> : <p className="text-muted">{t.common.empty}</p>}
              {!["CLOSED", "CANCELLED", "REFUNDED"].includes(o.status) && (
                <div className="mt-5 space-y-3">
                  <FileUploader value={extra} onChange={setExtra} />
                  {extra.length > 0 && <Button size="sm" onClick={async () => {
                    try { await api(`/orders/${o.id}/attachments`, { body: { attachment_ids: extra.map((f) => f.id) } }); setExtra([]); refresh(); } catch (e) { toast.error(errorMessage(e, t)); }
                  }}>{t.dash.addFiles}</Button>}
                </div>
              )}
            </Panel>
            <Panel title={t.dash.delivered}>
              {o.deliverables.length ? <div className="space-y-2">{o.deliverables.map((d) => d.attachment && <FileChip key={d.id} file={{ ...d.attachment, name: d.title || d.attachment.name }} />)}</div> : <EmptyState title={t.dash.noDeliverables} />}
            </Panel>
          </div>
        </TabsContent>
        <TabsContent value="payments">
          <Panel>
            {o.payments.length === 0 ? <p className="text-muted">{t.common.empty}</p> : (
              <ul className="divide-y divide-border text-[14px]">
                {o.payments.map((p) => (
                  <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <span><span className="font-medium">{p.provider}</span> <span className="text-muted">· {p.kind} · {p.reference} · {date(p.created_at, locale, true)}</span></span>
                    <span className="flex items-center gap-3"><Money minor={p.amount_minor} currency={p.currency} /><span className={p.status === "SUCCEEDED" ? "text-ok" : "text-muted"}>{p.status}</span></span>
                  </li>
                ))}
              </ul>
            )}
            {o.invoices.length > 0 && (
              <div className="mt-6 border-t border-border pt-4">
                <h3 className="mb-2 text-[14px] font-semibold">{t.dash.invoices}</h3>
                <ul className="space-y-1 text-[14px]">{o.invoices.map((i) => <li key={i.invoice_number} className="flex justify-between"><span className="tabular-nums">{i.invoice_number}</span><Money minor={i.amount_minor} currency={i.currency} /></li>)}</ul>
              </div>
            )}
          </Panel>
        </TabsContent>
        <TabsContent value="timeline"><Panel><Timeline events={o.events} /></Panel></TabsContent>
      </Tabs>
    </>
  );
}
