"use client";

import { CalendarClock, Handshake, MapPin, Package } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { Notice, Panel } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Handover, HandoverProposal, OrderDetail } from "@/types/api";

export function requirementLabel(t: ReturnType<typeof useI18n>["t"], key: string, value: string): [string, string] {
  const k = (t.biz.fields as Record<string, string>)[key] ?? key.replace(/_/g, " ");
  const v = (t.biz.opt as Record<string, string>)[value] ?? value;
  return [k, v];
}

function ProposalView({ p, label }: { p: HandoverProposal; label: string }) {
  const { locale } = useI18n();
  return (
    <div className="rounded-[12px] border border-border bg-surface p-3.5 text-[14px]">
      <p className="text-[12px] font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1.5 flex items-start gap-2"><MapPin className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />{p.place}</p>
      <p className="mt-1 flex items-center gap-2"><CalendarClock className="h-4 w-4 shrink-0 text-accent" aria-hidden />{date(p.time, locale, true)}</p>
      {p.note && <p className="mt-1.5 text-muted">{p.note}</p>}
    </div>
  );
}

function ProposeForm({ onSubmit, busy }: { onSubmit: (place: string, time: string, note: string) => void; busy: boolean }) {
  const { t } = useI18n();
  const [place, setPlace] = useState("");
  const [time, setTime] = useState("");
  const [note, setNote] = useState("");
  return (
    <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); if (place.trim() && time) onSubmit(place.trim(), new Date(time).toISOString(), note.trim()); }}>
      <Field label={t.biz.meetupPlace}>{(id) => <Input id={id} value={place} onChange={(e) => setPlace(e.target.value)} maxLength={300} placeholder={t.biz.meetupPlacePh} required />}</Field>
      <Field label={t.biz.meetupTime}>{(id) => <Input id={id} type="datetime-local" value={time} onChange={(e) => setTime(e.target.value)} min={new Date(Date.now() + 1800_000).toISOString().slice(0, 16)} required />}</Field>
      <Field label={t.biz.meetupNote} optional={t.common.optional}>{(id) => <Input id={id} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />}</Field>
      <Button type="submit" size="sm" variant="outline" loading={busy}>{t.biz.h.send}</Button>
    </form>
  );
}

function StatusLine({ h, admin }: { h: Handover; admin: boolean }) {
  const { t } = useI18n();
  const Icon = h.method === "PICKUP" ? Package : Handshake;
  return (
    <div className="flex items-start gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-tint-0 text-accent"><Icon className="h-5 w-5" aria-hidden /></span>
      <div>
        <p className="text-[12.5px] text-muted">{t.biz.h.method[h.method]}</p>
        <p className="font-medium">{(admin ? t.biz.h.statusAdmin : t.biz.h.status)[h.status]}</p>
      </div>
    </div>
  );
}

/** Customer view of a LOCAL order's pickup / meetup. */
export function HandoverPanel({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [other, setOther] = useState(false);
  const h = order.handover;
  if (!h) return null;
  const open = h.status !== "HANDED_OVER" && !["CANCELLED", "REFUNDED", "REFUND_PENDING", "CLOSED"].includes(order.status);
  async function call(path: string, body?: unknown) {
    setBusy(true);
    try { await api(`/orders/${order.id}/handover/${path}`, { body: body ?? {} }); setOther(false); onDone(); } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  return (
    <Panel title={t.biz.h.title}>
      <div className="space-y-4">
        <StatusLine h={h} admin={false} />
        {h.pickup_address && (
          <div className="rounded-[12px] border border-accent/40 bg-tint-0/60 p-3.5">
            <p className="text-[12px] font-medium uppercase tracking-wide text-accent">{t.biz.h.address}</p>
            <p className="mt-1 whitespace-pre-line text-[15px] font-medium">{h.pickup_address}</p>
          </div>
        )}
        {h.agreed && h.status === "CONFIRMED" && <ProposalView p={h.agreed} label={t.biz.h.agreed} />}
        {h.proposal && h.status !== "CONFIRMED" && h.method === "MEETUP" && <ProposalView p={h.proposal} label={t.biz.h.proposal} />}
        {open && order.remaining_minor > 0 && ["FINAL_PAYMENT_PENDING", "COMPLETED_PENDING_FINAL_PAYMENT"].includes(order.status) && <Notice>{t.biz.h.payFirst}</Notice>}
        {open && h.method === "MEETUP" && (
          <div className="flex flex-wrap gap-2">
            {h.status === "PROPOSED_BY_ADMIN" && <Button size="sm" onClick={() => call("accept")} loading={busy}>{t.biz.h.accept}</Button>}
            <Button size="sm" variant="ghost" onClick={() => setOther(!other)}>{t.biz.h.proposeOther}</Button>
          </div>
        )}
        {open && other && <ProposeForm busy={busy} onSubmit={(place, time, note) => call("propose", { place, time, note })} />}
      </div>
    </Panel>
  );
}

/** Owner view: confirm / counter-propose the meeting, and mark the paper result as handed over. */
export function AdminHandoverPanel({ order, onDone }: { order: OrderDetail; onDone: () => void }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [other, setOther] = useState(false);
  const h = order.handover;
  if (!h) return null;
  const open = h.status !== "HANDED_OVER" && !["CANCELLED", "REFUNDED", "REFUND_PENDING", "CLOSED"].includes(order.status);
  async function call(path: string, body?: unknown) {
    setBusy(true);
    try { await api(`/admin/orders/${order.id}/handover/${path}`, { body: body ?? {} }); setOther(false); toast.success(t.common.saved); onDone(); } catch (e) { toast.error(errorMessage(e, t)); } finally { setBusy(false); }
  }
  const canComplete = order.status === "READY_FOR_DELIVERY" && (h.method === "PICKUP" || h.status === "CONFIRMED");
  return (
    <Panel title={`${t.biz.h.title} · ${order.area?.name ?? ""}`}>
      <div className="space-y-4">
        <StatusLine h={h} admin />
        {h.method === "PICKUP" && h.pickup_address && <p className="text-[13px] text-muted">{t.biz.h.address}: {h.pickup_address}</p>}
        {h.agreed && <ProposalView p={h.agreed} label={t.biz.h.agreed} />}
        {h.proposal && h.status !== "CONFIRMED" && <ProposalView p={h.proposal} label={`${t.biz.h.proposal} (${h.proposal.by === "admin" ? "VIMORA" : order.customer?.full_name || "—"})`} />}
        {open && (
          <div className="flex flex-wrap gap-2">
            {h.status === "PROPOSED_BY_CUSTOMER" && <Button size="sm" onClick={() => call("confirm")} loading={busy}>{t.biz.h.confirm}</Button>}
            {h.method === "MEETUP" && <Button size="sm" variant="ghost" onClick={() => setOther(!other)}>{t.biz.h.proposeOther}</Button>}
            <Button size="sm" variant={canComplete ? "primary" : "outline"} disabled={!canComplete} onClick={() => call("complete")} loading={busy}>{t.biz.h.complete}</Button>
          </div>
        )}
        {open && <p className="text-[12.5px] text-muted">{t.biz.h.completeHint}</p>}
        {open && other && <ProposeForm busy={busy} onSubmit={(place, time, note) => call("propose", { place, time, note })} />}
      </div>
    </Panel>
  );
}
