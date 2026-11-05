"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Confirm, Dialog, Notice, Panel } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { pctOf } from "@/lib/money";
import { useI18n } from "@/lib/i18n/client";
import type { OrderDetail } from "@/types/api";
import { MoneyInput } from "./money-input";

type Line = { description: string; quantity: number; unit_price_minor: number };

export function QuoteBuilder({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [currency, setCurrency] = useState(order.currency || "UZS");
  const [lines, setLines] = useState<Line[]>([{ description: order.title, quantity: 1, unit_price_minor: 0 }]);
  const [discount, setDiscount] = useState(0);
  const [pct, setPct] = useState(30);
  const [days, setDays] = useState<string>("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const subtotal = lines.reduce((s, l) => s + l.quantity * l.unit_price_minor, 0);
  const total = Math.max(subtotal - discount, 0);
  const deposit = pctOf(total, pct, currency);
  async function submit() {
    setBusy(true);
    try {
      await api(`/admin/orders/${order.id}/quotations`, { body: { currency, line_items: lines, discount_minor: discount, deposit_percent: pct, estimated_delivery_days: days ? Number(days) : null, note } });
      setOpen(false); onDone();
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  return (
    <>
      <Button onClick={() => setOpen(true)}>{t.admin.createQuote}</Button>
      <Dialog wide open={open} onOpenChange={setOpen} title={t.admin.createQuote}
        footer={<Button loading={busy} onClick={submit}>{t.admin.issueQuote}</Button>}>
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={t.admin.currency}>{(id) => <Select id={id} value={currency} onChange={(e) => setCurrency(e.target.value)}><option>UZS</option><option>USD</option></Select>}</Field>
            <Field label={t.admin.depositPct}>{(id) => <Input id={id} type="number" min={0} max={100} value={pct} onChange={(e) => setPct(Math.min(100, Math.max(0, Number(e.target.value))))} />}</Field>
            <Field label={t.dash.deliveryDays.replace(": {n}", "").replace("{n}", "")}>{(id) => <Input id={id} type="number" min={0} value={days} onChange={(e) => setDays(e.target.value)} />}</Field>
          </div>
          <div className="space-y-2">
            {lines.map((l, i) => (
              <div key={i} className="grid grid-cols-[1fr_70px_140px_36px] gap-2">
                <Input aria-label={t.admin.description} value={l.description} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, description: e.target.value } : x))} />
                <Input aria-label={t.admin.qty} type="number" min={1} value={l.quantity} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, quantity: Math.max(1, Number(e.target.value)) } : x))} />
                <MoneyInput aria-label={t.admin.unitPrice} value={l.unit_price_minor} onChange={(m) => setLines(lines.map((x, j) => j === i ? { ...x, unit_price_minor: m } : x))} />
                <Button variant="ghost" size="icon" aria-label={t.common.remove} disabled={lines.length === 1} onClick={() => setLines(lines.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button>
              </div>
            ))}
            <Button variant="ghost" size="sm" onClick={() => setLines([...lines, { description: "", quantity: 1, unit_price_minor: 0 }])}><Plus className="h-4 w-4" />{t.admin.addLine}</Button>
          </div>
          <Field label={t.dash.discount}>{(id) => <MoneyInput id={id} value={discount} onChange={setDiscount} />}</Field>
          <Field label={t.admin.customerNotes}>{(id) => <Textarea id={id} value={note} onChange={(e) => setNote(e.target.value)} maxLength={4000} />}</Field>
          <dl className="space-y-1 border-t border-border pt-3 text-[14px]">
            <div className="flex justify-between font-semibold"><dt>{t.common.total}</dt><dd><Money minor={total} currency={currency} /></dd></div>
            <div className="flex justify-between text-muted"><dt>{t.common.deposit} (≈)</dt><dd><Money minor={deposit} currency={currency} /></dd></div>
            <p className="text-[12px] text-muted">The server recomputes totals and deposit authoritatively.</p>
          </dl>
        </div>
      </Dialog>
    </>
  );
}

export function StatusChanger({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const dedicated = new Set(["COMPLETED_PENDING_FINAL_PAYMENT", "READY_FOR_DELIVERY", "DELIVERED", "AI_PROCESSING", "REFUNDED", "QUOTATION_PENDING"]);
  const options = (order.allowed_transitions ?? []).filter((s) => !dedicated.has(s));
  const [to, setTo] = useState("");
  const [msg, setMsg] = useState("");
  const [visible, setVisible] = useState(true);
  if (!options.length) return <p className="text-[13.5px] text-muted">{t.admin.noTransitions}</p>;
  const st = t.status as Record<string, string>;
  const go = async () => {
    try { await api(`/admin/orders/${order.id}/status`, { body: { to_status: to, message: msg, customer_visible: visible } }); setTo(""); setMsg(""); onDone(); }
    catch (e) { toast.error(errorMessage(e, t)); }
  };
  return (
    <div className="space-y-3">
      <Select value={to} onChange={(e) => setTo(e.target.value)} aria-label={t.admin.changeStatus}>
        <option value="">{t.admin.changeStatus}</option>
        {options.map((s) => <option key={s} value={s}>{st[s] ?? s} ({s})</option>)}
      </Select>
      {to && (
        <>
          <Textarea value={msg} onChange={(e) => setMsg(e.target.value)} placeholder={t.admin.reason} rows={2} />
          <label className="flex items-center gap-2 text-[13.5px]"><input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} className="accent-[var(--accent)]" />{t.admin.customerNotes}</label>
          {to === "CANCELLED" ? (
            <Confirm danger title={t.dash.cancel} body={t.dash.cancelConfirm} confirmLabel={t.common.confirm} onConfirm={go} trigger={<Button variant="danger" size="sm">{t.common.confirm}</Button>} />
          ) : <Button size="sm" onClick={go}>{t.common.confirm}</Button>}
        </>
      )}
    </div>
  );
}

export function DeliverableUpload({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const ref = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState("");
  async function upload() {
    const f = ref.current?.files?.[0];
    if (!f || !title.trim()) return;
    const form = new FormData();
    form.append("file", f); form.append("title", title); form.append("note", "");
    setBusy(true);
    try { await api(`/admin/orders/${order.id}/files`, { form }); setTitle(""); setFileName(""); if (ref.current) ref.current.value = ""; onDone(); }
    catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-2">
      <Input placeholder={t.admin.deliverableTitle} value={title} onChange={(e) => setTitle(e.target.value)} aria-label={t.admin.deliverableTitle} />
      <input ref={ref} type="file" className="sr-only" aria-label={t.common.upload} onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")} />
      <button type="button" onClick={() => ref.current?.click()} className="w-full truncate rounded-[6px] border border-dashed border-border px-3 py-2.5 text-left text-[13.5px] text-muted hover:border-fg/40 hover:text-fg">
        {fileName || t.common.upload}
      </button>
      <Button size="sm" variant="outline" loading={busy} disabled={!fileName || !title.trim()} onClick={upload}>{t.admin.uploadDeliverable}</Button>
    </div>
  );
}

export function MoneyTools({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const [open, setOpen] = useState<null | "manual" | "refund">(null);
  const [amount, setAmount] = useState(order.payment_due?.amount_minor ?? 0);
  const [ref, setRef] = useState("");
  const [paymentId, setPaymentId] = useState<number | null>(order.payments.find((p) => p.status === "SUCCEEDED")?.id ?? null);
  const [busy, setBusy] = useState(false);
  async function run(path: string, body: unknown) {
    setBusy(true);
    try { await api(path, { body }); setOpen(null); onDone(); } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  const succeeded = order.payments.filter((p) => p.status === "SUCCEEDED");
  return (
    <div className="flex flex-wrap gap-2">
      {order.payment_due && <Button size="sm" variant="outline" onClick={() => { setAmount(order.payment_due!.amount_minor); setOpen("manual"); }}>{t.admin.manualPayment}</Button>}
      {succeeded.length > 0 && <Button size="sm" variant="ghost" onClick={() => { setAmount(succeeded[0]!.amount_minor); setOpen("refund"); }}>{t.admin.refund}</Button>}
      <Dialog open={open === "manual"} onOpenChange={(o) => !o && setOpen(null)} title={t.admin.manualPayment}
        footer={<Button loading={busy} onClick={() => run(`/admin/orders/${order.id}/manual-payment`, { amount_minor: amount, reference: ref, note: "" })}>{t.common.confirm}</Button>}>
        <div className="space-y-4">
          <Notice tone="warn">Only record money you have actually received and verified in your bank or cash records. This is audited.</Notice>
          <Field label={`${t.common.amount} (${order.currency})`} hint={order.payment_due ? `${t.common.deposit}/${t.common.remaining}: ${order.payment_due.amount_minor / 100} · ${t.common.total}: ${order.payment_due.full_amount_minor / 100}` : undefined}>
            {(id) => <MoneyInput id={id} value={amount} onChange={setAmount} />}
          </Field>
          <Field label={t.admin.reference}>{(id) => <Input id={id} value={ref} onChange={(e) => setRef(e.target.value)} placeholder="Bank transfer #" />}</Field>
        </div>
      </Dialog>
      <Dialog open={open === "refund"} onOpenChange={(o) => !o && setOpen(null)} title={t.admin.requestRefund}
        footer={<Button variant="danger" loading={busy} onClick={() => run(`/admin/orders/${order.id}/refunds`, { payment_id: paymentId, amount_minor: amount, reason: ref })}>{t.admin.requestRefund}</Button>}>
        <div className="space-y-4">
          <Field label={t.admin.payment}>{(id) => <Select id={id} value={paymentId ?? ""} onChange={(e) => setPaymentId(Number(e.target.value))}>{succeeded.map((p) => <option key={p.id} value={p.id}>{p.reference} · {p.provider} · {p.amount_minor / 100} {p.currency}</option>)}</Select>}</Field>
          <Field label={t.common.amount}>{(id) => <MoneyInput id={id} value={amount} onChange={setAmount} />}</Field>
          <Field label={t.admin.reason}>{(id) => <Textarea id={id} value={ref} onChange={(e) => setRef(e.target.value)} />}</Field>
        </div>
      </Dialog>
    </div>
  );
}

export function NotesEditor({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const [admin, setAdmin] = useState(order.admin_notes ?? "");
  const [cust, setCust] = useState(order.customer_notes ?? "");
  return (
    <Panel title={t.admin.adminNotes}>
      <div className="space-y-3">
        <Textarea value={admin} onChange={(e) => setAdmin(e.target.value)} aria-label={t.admin.adminNotes} rows={3} />
        <Field label={t.admin.customerNotes}>{(id) => <Textarea id={id} value={cust} onChange={(e) => setCust(e.target.value)} rows={2} />}</Field>
        <Button size="sm" variant="outline" onClick={async () => { try { await api(`/admin/orders/${order.id}`, { method: "PATCH", body: { admin_notes: admin, customer_notes: cust } }); toast.success(t.common.saved); onDone(); } catch (e) { toast.error(errorMessage(e, t)); } }}>{t.common.save}</Button>
      </div>
    </Panel>
  );
}
