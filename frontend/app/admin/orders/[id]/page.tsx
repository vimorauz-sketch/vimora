"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { FileChip, Money, StageRail, StatusBadge } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Confirm, Dialog, ErrorState, LoadingRows, Notice, Panel, Tabs, TabsContent, TabsList } from "@/components/ui/misc";
import { DeliverableUpload, MoneyTools, NotesEditor, QuoteBuilder, StatusChanger } from "@/features/admin/order-tools";
import { AdminHandoverPanel, requirementLabel } from "@/features/local/handover";
import { MessageThread } from "@/features/messages";
import { Timeline } from "@/features/timeline";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { OrderDetail } from "@/types/api";

const CAPS = ["document_writing", "translation", "data_transformation", "code_generation", "summarization"];

export default function AdminOrderPage() {
  const { t, locale } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { data: me } = useMe();
  const can = (p: string) => !!me?.permissions.includes(p);
  const q = useQuery({ queryKey: ["admin-order", id], queryFn: () => api<OrderDetail>(`/admin/orders/${id}`), refetchInterval: 20_000 });
  const [aiOpen, setAiOpen] = useState(false);
  const [cap, setCap] = useState("");
  const [instr, setInstr] = useState("");
  const action = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) => api(path, { method: "POST", body: body ?? {} }),
    onSuccess: () => q.refetch(),
    onError: (e) => toast.error(errorMessage(e, t)),
  });
  if (q.isLoading) return <LoadingRows rows={8} />;
  if (q.error || !q.data) return <ErrorState message={errorMessage(q.error, t)} onRetry={() => q.refetch()} />;
  const o = q.data;
  const refresh = () => void q.refetch();
  const approvedUnreleased = o.deliverables.filter((d) => d.approved_at && !d.released_at);
  const working = ["QUEUED", "MANUAL_PROCESSING", "REVISION_REQUESTED", "AI_REVIEW_REQUIRED", "AI_PROCESSING"].includes(o.status);
  return (
    <>
      <div className="mb-8">
        <Link href="/admin/orders" className="text-[13px] text-muted hover:text-fg">{t.admin.orders}</Link>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="display text-[26px]"><span className="tabular-nums text-muted">#{o.order_number}</span> {o.title}</h1>
          <StatusBadge status={o.status} staff />
        </div>
        <p className="mt-1 text-[13.5px] text-muted">
          {o.customer && <Link className="underline-offset-4 hover:underline" href={`/admin/customers/${o.customer.id}`}>{o.customer.full_name || o.customer.email} · {o.customer.email}</Link>} · {o.service_name ?? t.admin.custom} · {date(o.created_at, locale, true)}
          {o.execution_method && o.execution_method !== "UNASSIGNED" && ` · ${o.execution_method}`}
        </p>
        <div className="mt-5 max-w-3xl"><StageRail status={o.status} /></div>
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="min-w-0">
          <Tabs defaultValue="request">
            <TabsList items={[{ value: "request", label: t.dash.tabs.summary }, { value: "messages", label: t.dash.tabs.messages }, { value: "files", label: t.dash.tabs.files }, { value: "payments", label: t.dash.tabs.payments }, { value: "timeline", label: t.dash.tabs.timeline }]} />
            <TabsContent value="request" className="space-y-6">
              <Panel title={t.dash.order}>
                <p className="whitespace-pre-line">{o.description}</p>
                {Object.keys(o.requirements).length > 0 && <dl className="mt-4 grid gap-2 border-t border-border pt-4 text-[14px] sm:grid-cols-2">{Object.entries(o.requirements).map(([k, v]) => { const [kl, vl] = requirementLabel(t, k, v); return <div key={k}><dt className="text-muted">{kl}</dt><dd>{vl}</dd></div>; })}</dl>}
                <dl className="mt-4 grid gap-2 border-t border-border pt-4 text-[13.5px] sm:grid-cols-3">
                  <div><dt className="text-muted">{t.custom.language}</dt><dd>{o.preferred_language}</dd></div>
                  {o.deadline && <div><dt className="text-muted">{t.custom.deadline}</dt><dd>{date(o.deadline, locale)}</dd></div>}
                  {Object.entries((o as unknown as { contact_info: Record<string, string> }).contact_info ?? {}).map(([k, v]) => <div key={k}><dt className="text-muted">{k}</dt><dd>{v}</dd></div>)}
                </dl>
              </Panel>
              {o.quotations.length > 0 && (
                <Panel title={t.dash.quotation}>
                  <ul className="divide-y divide-border text-[14px]">
                    {o.quotations.map((qq) => (
                      <li key={qq.id} className="flex flex-wrap justify-between gap-2 py-2.5">
                        <span>{qq.status} · {qq.source} · {date(qq.created_at, locale, true)}{qq.rejection_reason && <span className="block text-muted">“{qq.rejection_reason}”</span>}</span>
                        <span><Money minor={qq.total_minor} currency={qq.currency} /> <span className="text-muted">/ <Money minor={qq.deposit_minor} currency={qq.currency} /></span></span>
                      </li>
                    ))}
                  </ul>
                </Panel>
              )}
              {(o.ai_executions?.length ?? 0) > 0 && (
                <Panel title={t.admin.executions}>
                  <ul className="divide-y divide-border text-[14px]">
                    {o.ai_executions!.map((ex) => (
                      <li key={ex.id}><Link href={`/admin/ai/${ex.id}`} className="flex justify-between gap-3 py-2.5 hover:text-accent">
                        <span>#{ex.attempt} · {ex.capability ?? "auto"} · {date(ex.created_at, locale, true)}</span>
                        <span className={ex.status === "REVIEW_REQUIRED" ? "text-accent" : ex.status === "FAILED" ? "text-danger" : "text-muted"}>{ex.status}</span>
                      </Link></li>
                    ))}
                  </ul>
                </Panel>
              )}
              {o.can_review === false && o.review_rating && (
                <Panel title={t.admin.reviews}>
                  <p className="text-accent">{"★".repeat(o.review_rating)}</p>
                  <p className="mt-1">{o.review_text}</p>
                  <Button size="sm" variant="outline" className="mt-3" onClick={() => action.mutate({ path: `/admin/orders/${o.id}/review-visibility`, body: { public: !o.review_public } })}>{o.review_public ? t.admin.hide : t.admin.makePublic}</Button>
                </Panel>
              )}
              {can("orders.manage") && <NotesEditor order={o} onDone={refresh} />}
            </TabsContent>
            <TabsContent value="messages"><Panel><MessageThread orderId={o.id} staff /></Panel></TabsContent>
            <TabsContent value="files" className="space-y-6">
              <Panel title={t.dash.yourFiles}>{o.attachments.length ? <div className="grid gap-2 sm:grid-cols-2">{o.attachments.map((a) => <FileChip key={a.id} file={a} />)}</div> : <p className="text-muted">{t.common.empty}</p>}</Panel>
              <Panel title={t.dash.deliverables}>
                {o.deliverables.length ? (
                  <ul className="space-y-2">
                    {o.deliverables.map((d) => (
                      <li key={d.id} className="flex items-center gap-3">
                        <div className="flex-1">{d.attachment && <FileChip file={{ ...d.attachment, name: `${d.title} (${d.source}${d.released_at ? ", released" : ""})` }} />}</div>
                        {!d.released_at && can("deliverables.manage") && <Confirm danger title={t.common.delete} confirmLabel={t.common.delete} onConfirm={() => action.mutateAsync({ path: "", body: null }).catch(() => undefined).then(() => api(`/admin/orders/${o.id}/deliverables/${d.id}`, { method: "DELETE" })).then(refresh)}
                          trigger={<Button variant="ghost" size="sm">{t.common.delete}</Button>} />}
                      </li>
                    ))}
                  </ul>
                ) : <p className="text-muted">{t.common.empty}</p>}
              </Panel>
              {(o.ai_outputs?.length ?? 0) > 0 && <Panel title={t.admin.aiOutputs}><div className="grid gap-2 sm:grid-cols-2">{o.ai_outputs!.map((a) => <FileChip key={a.id} file={a} />)}</div></Panel>}
            </TabsContent>
            <TabsContent value="payments">
              <Panel>
                {o.payments.length === 0 ? <p className="text-muted">{t.common.empty}</p> : (
                  <ul className="divide-y divide-border text-[14px]">{o.payments.map((p) => (
                    <li key={p.id} className="flex flex-wrap justify-between gap-3 py-3">
                      <span>{p.provider} · {p.kind} · <span className="tabular-nums">{p.reference}</span>{p.provider_transaction_id && <span className="block text-[12.5px] text-muted">txn {p.provider_transaction_id}</span>}</span>
                      <span><Money minor={p.amount_minor} currency={p.currency} /> <span className={p.status === "SUCCEEDED" ? "text-ok" : "text-muted"}>{p.status}</span></span>
                    </li>
                  ))}</ul>
                )}
              </Panel>
            </TabsContent>
            <TabsContent value="timeline"><Panel><Timeline events={o.events} staff /></Panel></TabsContent>
          </Tabs>
        </div>
        <aside className="space-y-5">
          {o.handover && <AdminHandoverPanel order={o} onDone={refresh} />}
          <Panel title={t.common.total}>
            <dl className="space-y-1.5 text-[14px]">
              <div className="flex justify-between"><dt className="text-muted">{t.common.total}</dt><dd><Money minor={o.total_minor} currency={o.currency} /></dd></div>
              <div className="flex justify-between"><dt className="text-muted">{t.common.deposit}</dt><dd><Money minor={o.deposit_minor} currency={o.currency} /></dd></div>
              <div className="flex justify-between"><dt className="text-muted">{t.common.paid}</dt><dd><Money minor={o.paid_minor} currency={o.currency} /></dd></div>
              <div className="flex justify-between font-medium"><dt>{t.common.remaining}</dt><dd><Money minor={o.remaining_minor} currency={o.currency} /></dd></div>
            </dl>
            {can("finance.manage") && <div className="mt-4"><MoneyTools order={o} onDone={refresh} /></div>}
          </Panel>
          {can("quotations.manage") && ["SUBMITTED", "UNDER_REVIEW", "QUOTATION_PENDING"].includes(o.status) && <Panel title={t.dash.quotation}><QuoteBuilder order={o} onDone={refresh} /></Panel>}
          {working && can("ai.operate") && (
            <Panel title={t.admin.ai}>
              {o.status === "AI_REVIEW_REQUIRED" && o.ai_executions?.[0] && <Button asChild className="mb-3 w-full"><Link href={`/admin/ai/${o.ai_executions[0].id}`}>{t.admin.review}</Link></Button>}
              {o.status !== "AI_PROCESSING" && <Button variant="outline" className="w-full" onClick={() => setAiOpen(true)}>{t.admin.startAi}</Button>}
              {o.status === "AI_PROCESSING" && <p className="text-[14px] text-muted">{t.status.AI_PROCESSING}…</p>}
            </Panel>
          )}
          {can("deliverables.manage") && (working || (o.status === "READY_FOR_DELIVERY" && !o.is_local)) && (
            <Panel title={t.dash.deliverables}>
              {o.status !== "READY_FOR_DELIVERY" && <DeliverableUpload order={o} onDone={refresh} />}
              {working && o.status !== "AI_PROCESSING" && (
                <div className="mt-4 border-t border-border pt-4">
                  <p className="mb-2 text-[13px] text-muted">{t.admin.completeHint}</p>
                  <Button className="w-full" disabled={!approvedUnreleased.length && !o.is_local} loading={action.isPending} onClick={() => action.mutate({ path: `/admin/orders/${o.id}/complete` })}>{t.admin.completeWork}</Button>
                </div>
              )}
              {o.status === "READY_FOR_DELIVERY" && !o.is_local && (
                <div>
                  <p className="mb-2 text-[13px] text-muted">{t.admin.releaseHint}</p>
                  <Confirm title={t.admin.release} body={`${approvedUnreleased.length} file(s)`} confirmLabel={t.admin.release} onConfirm={() => action.mutateAsync({ path: `/admin/orders/${o.id}/release` })}
                    trigger={<Button className="w-full">{t.admin.release}</Button>} />
                </div>
              )}
            </Panel>
          )}
          {o.status === "FINAL_PAYMENT_PENDING" && <Notice>{t.status.FINAL_PAYMENT_PENDING}: <Money minor={o.remaining_minor} currency={o.currency} /></Notice>}
          {can("orders.manage") && <Panel title={t.admin.changeStatus}><StatusChanger order={o} onDone={refresh} /></Panel>}
        </aside>
      </div>
      <Dialog open={aiOpen} onOpenChange={setAiOpen} title={t.admin.startAi}
        footer={<Button loading={action.isPending} onClick={() => action.mutate({ path: `/admin/orders/${o.id}/ai/start`, body: { capability: cap || null, instructions: instr || null } }, { onSuccess: () => setAiOpen(false) })}>{t.admin.startAi}</Button>}>
        <div className="space-y-4">
          <Field label={t.admin.capability}>{(id) => <Select id={id} value={cap} onChange={(e) => setCap(e.target.value)}><option value="">auto / service default</option>{CAPS.map((c) => <option key={c}>{c}</option>)}</Select>}</Field>
          <Field label={t.admin.instructions} optional={t.common.optional}>{(id) => <Textarea id={id} value={instr} onChange={(e) => setInstr(e.target.value)} />}</Field>
        </div>
      </Dialog>
    </>
  );
}
