"use client";

import { Check, FileText, Paperclip, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { api, errorMessage } from "@/lib/api";
import { bytes, cn, money } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Attachment } from "@/types/api";
import { Button } from "./ui/button";

const STAGE_OF: Record<string, number> = {
  DRAFT: 0, SUBMITTED: 0, UNDER_REVIEW: 1, QUOTATION_PENDING: 1, QUOTATION_ACCEPTED: 2, DEPOSIT_PENDING: 2, PARTIALLY_PAID: 3, PAID: 3, QUEUED: 3,
  AI_PROCESSING: 3, MANUAL_PROCESSING: 3, REVISION_REQUESTED: 3, AI_REVIEW_REQUIRED: 4, COMPLETED_PENDING_FINAL_PAYMENT: 5, FINAL_PAYMENT_PENDING: 5,
  READY_FOR_DELIVERY: 5, DELIVERED: 6, CLOSED: 6,
};
const CUSTOMER_ACTION = new Set(["QUOTATION_PENDING", "DEPOSIT_PENDING", "FINAL_PAYMENT_PENDING", "DELIVERED"]);
const NEGATIVE = new Set(["CANCELLED", "REFUND_PENDING", "REFUNDED", "FAILED"]);

export function needsCustomerAction(status: string) {
  return CUSTOMER_ACTION.has(status);
}

export function StatusBadge({ status, staff }: { status: string; staff?: boolean }) {
  const { t } = useI18n();
  const label = (t.status as Record<string, string>)[status] ?? status;
  const actionable = staff ? ["SUBMITTED", "UNDER_REVIEW", "AI_REVIEW_REQUIRED", "READY_FOR_DELIVERY", "REVISION_REQUESTED", "QUEUED", "REFUND_PENDING"].includes(status) : CUSTOMER_ACTION.has(status);
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-[5px] border px-2 py-0.5 text-[12.5px]",
      actionable ? "border-accent/70 text-fg" : NEGATIVE.has(status) ? "border-danger/40 text-danger" : "border-border text-muted")}>
      <span className={cn("h-1.5 w-1.5 rounded-full", actionable ? "bg-accent" : NEGATIVE.has(status) ? "bg-danger" : "bg-muted/60")} aria-hidden />
      {label}
    </span>
  );
}

/** The VIMORA stage rail: six real stages of an order. Lime marks completed stages and the current one. */
export function StageRail({ status, compact }: { status?: string; compact?: boolean }) {
  const { t } = useI18n();
  const current = status ? STAGE_OF[status] ?? -1 : -1;
  const stopped = status ? NEGATIVE.has(status) : false;
  return (
    <ol className={cn("grid grid-cols-6", compact ? "gap-1" : "gap-1.5")} aria-label="Order progress">
      {t.stage.map((label, i) => {
        const done = !stopped && i < current;
        const active = !stopped && i === current;
        return (
          <li key={label} className="min-w-0" aria-current={active ? "step" : undefined}>
            <div className={cn("h-[3px] rounded-full", done ? "bg-accent" : active ? "bg-accent/60" : "bg-border")} />
            {!compact && <p className={cn("mt-2 truncate text-[12px]", done || active ? "text-fg" : "text-muted")}>{label}</p>}
          </li>
        );
      })}
    </ol>
  );
}

export function Money({ minor, currency, className }: { minor: number | null | undefined; currency: string; className?: string }) {
  const { locale } = useI18n();
  return <span className={cn("tabular-nums", className)}>{money(minor, currency, locale)}</span>;
}

export async function openDownload(id: number, t: { errors: Record<string, string> }) {
  try {
    const { url } = await api<{ url: string }>(`/files/${id}/link`);
    window.location.assign(url);
  } catch (e) {
    toast.error(errorMessage(e, t));
  }
}

export function FileChip({ file, onRemove }: { file: Attachment; onRemove?: () => void }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-2.5 rounded-[6px] border border-border px-3 py-2 text-[13.5px]">
      <FileText className="h-4 w-4 shrink-0 text-muted" aria-hidden />
      <button type="button" className="min-w-0 flex-1 truncate text-left hover:underline" onClick={() => openDownload(file.id, t)}>{file.name}</button>
      <span className="shrink-0 text-[12px] text-muted">{bytes(file.size_bytes)}</span>
      {onRemove && <button type="button" onClick={onRemove} aria-label={t.common.remove} className="text-muted hover:text-fg"><X className="h-3.5 w-3.5" /></button>}
    </div>
  );
}

/** Uploads files immediately (server validates type/size/content) and returns attachment ids. */
export function FileUploader({ value, onChange, purpose = "ORDER_INPUT", maxMb = 25, compact }: { value: Attachment[]; onChange: (v: Attachment[]) => void; purpose?: "ORDER_INPUT" | "MESSAGE"; maxMb?: number; compact?: boolean }) {
  const { t } = useI18n();
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  async function handle(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    const added: Attachment[] = [];
    for (const f of Array.from(files)) {
      if (f.size > maxMb * 1024 * 1024) { toast.error(`${f.name}: > ${maxMb} MB`); continue; }
      const form = new FormData();
      form.append("file", f);
      form.append("purpose", purpose);
      try { added.push(await api<Attachment>("/files", { form })); } catch (e) { toast.error(`${f.name}: ${errorMessage(e, t)}`); }
    }
    onChange([...value, ...added]);
    setBusy(false);
    if (ref.current) ref.current.value = "";
  }
  return (
    <div className="space-y-2">
      <input ref={ref} type="file" multiple className="sr-only" onChange={(e) => handle(e.target.files)} aria-label={t.common.upload}
        accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.txt,.md,.csv,.json,.docx,.xlsx,.pptx,.zip,.mp3,.wav,.mp4,.mov" />
      {compact ? (
        <Button type="button" variant="ghost" size="icon" onClick={() => ref.current?.click()} loading={busy} aria-label={t.common.upload}><Paperclip className="h-4 w-4" /></Button>
      ) : (
        <button type="button" onClick={() => ref.current?.click()} disabled={busy}
          className="flex w-full items-center gap-3 rounded-[8px] border border-dashed border-border px-4 py-4 text-left text-[14px] text-muted transition-colors hover:border-fg/40 hover:text-fg">
          <Upload className="h-4 w-4" aria-hidden /> {busy ? t.common.uploading : t.common.upload}
        </button>
      )}
      {value.length > 0 && <div className="grid gap-2 sm:grid-cols-2">{value.map((f) => <FileChip key={f.id} file={f} onRemove={() => onChange(value.filter((x) => x.id !== f.id))} />)}</div>}
    </div>
  );
}

export function CheckItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-accent text-accent-fg"><Check className="h-3 w-3" aria-hidden /></span>
      <span>{children}</span>
    </li>
  );
}
