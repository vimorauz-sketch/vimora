"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/field";
import { Confirm, Dialog, Notice, Panel } from "@/components/ui/misc";
import { useSite } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { date, money } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { OrderDetail, Payment, Quotation } from "@/types/api";

export function QuotationCard({ order, q, onDone }: { order: OrderDetail; q: Quotation; onDone: () => void }) {
  const { t, locale } = useI18n();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = q.status === "PENDING" && order.status === "QUOTATION_PENDING";
  async function act(kind: "accept" | "reject") {
    setBusy(true);
    try { await api(`/orders/${order.id}/quotation/${kind}`, { body: { quotation_id: q.id, reason } }); setRejecting(false); onDone(); }
    catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  return (
    <Panel title={pending ? t.dash.quotationPending : t.dash.quotation} className={pending ? "border-accent/60" : undefined}>
      <table className="w-full text-[14px]">
        <caption className="sr-only">{t.dash.lineItems}</caption>
        <tbody className="divide-y divide-border">
          {q.line_items.map((li, i) => (
            <tr key={i}><td className="py-2 pr-4">{li.description}{li.quantity > 1 && <span className="text-muted"> × {li.quantity}</span>}</td><td className="py-2 text-right tabular-nums"><Money minor={li.total_minor} currency={q.currency} /></td></tr>
          ))}
          {q.discount_minor > 0 && <tr><td className="py-2 text-muted">{t.dash.discount}</td><td className="py-2 text-right">−<Money minor={q.discount_minor} currency={q.currency} /></td></tr>}
          {q.extra_charges_minor > 0 && !q.line_items.length && <tr><td className="py-2 text-muted">{t.dash.extras}</td><td className="py-2 text-right"><Money minor={q.extra_charges_minor} currency={q.currency} /></td></tr>}
        </tbody>
      </table>
      <dl className="mt-4 space-y-1.5 border-t border-border pt-4 text-[14px]">
        <div className="flex justify-between text-[17px] font-semibold"><dt>{t.common.total}</dt><dd><Money minor={q.total_minor} currency={q.currency} /></dd></div>
        <div className="flex justify-between"><dt className="text-muted">{t.services.depositShare}</dt><dd><Money minor={q.deposit_minor} currency={q.currency} /></dd></div>
        <div className="flex justify-between"><dt className="text-muted">{t.services.payOnDelivery}</dt><dd><Money minor={q.remaining_minor} currency={q.currency} /></dd></div>
      </dl>
      {q.estimated_delivery_days !== null && <p className="mt-3 text-[13.5px] text-muted">{t.dash.deliveryDays.replace("{n}", String(q.estimated_delivery_days))}</p>}
      {q.note && <p className="mt-3 whitespace-pre-line text-[14px]">{q.note}</p>}
      {pending && (
        <>
          {q.valid_until && <p className="mt-3 text-[12.5px] text-muted">{t.dash.validUntil}: {date(q.valid_until, locale)}</p>}
          <div className="mt-5 flex flex-wrap gap-2">
            <Button onClick={() => act("accept")} loading={busy}>{t.dash.accept}</Button>
            <Button variant="outline" onClick={() => setRejecting(true)}>{t.dash.reject}</Button>
          </div>
          <Dialog open={rejecting} onOpenChange={setRejecting} title={t.dash.reject} footer={<Button variant="danger" loading={busy} onClick={() => act("reject")}>{t.dash.reject}</Button>}>
            <Field label={t.dash.rejectReason}>{(id) => <Textarea id={id} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={2000} />}</Field>
          </Dialog>
        </>
      )}
      {!pending && <p className="mt-4 text-[13px] text-muted">{(t.status as Record<string, string>)[order.status]} · {money(q.total_minor, q.currency, locale)}</p>}
    </Panel>
  );
}

export function PaymentPanel({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t, locale } = useI18n();
  const { data: site } = useSite();
  const [busy, setBusy] = useState<string | null>(null);
  const [instructions, setInstructions] = useState<string | null>(null);
  const due = order.payment_due;
  if (!due) return null;
  const providers = (site?.["payments.providers"] ?? []).filter((p) => p.currencies.includes(order.currency));
  const available = providers.filter((p) => p.available);
  async function pay(provider: string, full: boolean) {
    setBusy(provider + full);
    try {
      const r = await api<{ redirect_url: string | null; instructions: string | null }>(`/orders/${order.id}/payments`, {
        body: { provider, pay_full: full }, headers: { "Idempotency-Key": `${order.id}-${provider}-${full}-${order.paid_minor}` },
      });
      if (r.redirect_url) window.location.assign(r.redirect_url);
      else { setInstructions(r.instructions); onDone(); }
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(null); }
  }
  const showFull = due.kind === "DEPOSIT" && due.full_amount_minor > due.amount_minor;
  return (
    <Panel title={t.dash.choosePayment} className="border-accent/60">
      <p className="text-[22px] font-semibold"><Money minor={due.amount_minor} currency={due.currency} /></p>
      <p className="text-[13.5px] text-muted">{due.kind === "DEPOSIT" ? t.services.depositShare : t.common.remaining}</p>
      {available.length === 0 ? <div className="mt-4"><Notice tone="warn">{t.dash.noProviders}</Notice></div> : (
        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          {providers.map((p) => (
            <Button key={p.key} variant={p.available ? "outline" : "ghost"} disabled={!p.available} loading={busy === p.key + "false"} onClick={() => pay(p.key, false)}
              title={p.available ? undefined : t.common.configRequired} className="justify-between">
              <span>{p.key === "MANUAL" ? t.dash.manualInstructions : p.key.charAt(0) + p.key.slice(1).toLowerCase()}</span>
              {!p.available && <span className="text-[12px] text-muted">{t.common.unavailable}</span>}
            </Button>
          ))}
        </div>
      )}
      {showFull && available.length > 0 && (
        <div className="mt-4 border-t border-border pt-4">
          <p className="mb-2 text-[13.5px] text-muted">{t.dash.payFull.replace("{amount}", money(due.full_amount_minor, due.currency, locale))}</p>
          <div className="flex flex-wrap gap-2">{available.map((p) => <Button key={p.key} size="sm" variant="ghost" loading={busy === p.key + "true"} onClick={() => pay(p.key, true)}>{p.key}</Button>)}</div>
        </div>
      )}
      {instructions && <div className="mt-4"><Notice><p className="font-medium">{t.dash.manualInstructions}</p><p className="mt-1 whitespace-pre-line">{instructions}</p></Notice></div>}
    </Panel>
  );
}

/** After returning from a provider we poll our own server; the redirect itself proves nothing. */
export function PaymentReturnWatcher({ orderId }: { orderId: number }) {
  const { t } = useI18n();
  const ref = useSearchParams().get("payment");
  const [started] = useState(() => Date.now());
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["payment-status", orderId, ref],
    queryFn: () => api<{ payment: Payment; confirmed: boolean }>(`/orders/${orderId}/payments/${encodeURIComponent(ref ?? "")}`),
    enabled: !!ref,
    refetchInterval: (query) => (query.state.data?.confirmed || (query.state.dataUpdateCount ?? 0) > 40 ? false : 3000),
  });
  useEffect(() => { if (q.data?.confirmed) void qc.invalidateQueries({ queryKey: ["order", orderId] }); }, [q.data?.confirmed, qc, orderId]);
  if (!ref || !q.data) return null;
  if (q.data.confirmed) return <Notice tone="accent">{t.dash.paymentConfirmed}</Notice>;
  if (["FAILED", "CANCELLED"].includes(q.data.payment.status)) return <Notice tone="warn">{(t.status as Record<string, string>).FAILED}</Notice>;
  return <Notice>{q.dataUpdatedAt - (q.errorUpdatedAt || 0) > 0 && Date.now() - started > 15_000 ? t.dash.paymentNotConfirmed : t.dash.paymentPending}</Notice>;
}

export function DeliveredActions({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const [mode, setMode] = useState<null | "revision" | "review">(null);
  const [note, setNote] = useState("");
  const [rating, setRating] = useState(5);
  const [busy, setBusy] = useState(false);
  async function run(path: string, body: unknown, ok?: string) {
    setBusy(true);
    try { await api(`/orders/${order.id}/${path}`, { body }); if (ok) toast.success(ok); setMode(null); onDone(); } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  return (
    <div className="flex flex-wrap gap-2">
      {order.status === "DELIVERED" && <Button onClick={() => run("close", {})} loading={busy}>{t.dash.acceptWork}</Button>}
      {order.can_request_revision && <Button variant="outline" onClick={() => setMode("revision")}>{t.dash.requestRevision}</Button>}
      {order.can_review && <Button variant="ghost" onClick={() => setMode("review")}>{t.dash.review}</Button>}
      <Dialog open={mode === "revision"} onOpenChange={(o) => !o && setMode(null)} title={t.dash.requestRevision}
        footer={<Button loading={busy} disabled={note.trim().length < 5} onClick={() => run("revision", { note })}>{t.common.send}</Button>}>
        <Field label={t.dash.revisionNote}>{(id) => <Textarea id={id} value={note} onChange={(e) => setNote(e.target.value)} maxLength={4000} />}</Field>
      </Dialog>
      <Dialog open={mode === "review"} onOpenChange={(o) => !o && setMode(null)} title={t.dash.review}
        footer={<Button loading={busy} onClick={() => run("review", { rating, text: note }, t.dash.reviewThanks)}>{t.common.send}</Button>}>
        <fieldset className="mb-4"><legend className="mb-2 text-[13px] font-medium">{t.dash.rating}</legend>
          <div className="flex gap-1">{[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" onClick={() => setRating(n)} aria-pressed={rating === n} aria-label={`${n}/5`} className={`text-[24px] ${n <= rating ? "text-accent" : "text-border"}`}>★</button>
          ))}</div>
        </fieldset>
        <Field label={t.dash.reviewText}>{(id) => <Textarea id={id} value={note} onChange={(e) => setNote(e.target.value)} maxLength={3000} />}</Field>
      </Dialog>
    </div>
  );
}

export function CancelOrder({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  if (!order.can_cancel) return null;
  return (
    <Confirm danger title={t.dash.cancel} body={t.dash.cancelConfirm} confirmLabel={t.dash.cancel}
      onConfirm={async () => { try { await api(`/orders/${order.id}/cancel`, { body: { reason: "" } }); onDone(); } catch (e) { toast.error(errorMessage(e, t)); } }}
      trigger={<Button variant="danger" size="sm">{t.dash.cancel}</Button>} />
  );
}
