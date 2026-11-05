"use client";

import * as AlertDialog from "@radix-ui/react-alert-dialog";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { AlertTriangle, Inbox, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import { Button } from "./button";

export function Panel({ children, className, title, actions }: { children: ReactNode; className?: string; title?: ReactNode; actions?: ReactNode }) {
  return (
    <section className={cn("card", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-border px-5 py-3.5">
          {title && <h2 className="text-[14px] font-semibold">{title}</h2>}
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function PageHeader({ title, sub, actions }: { title: ReactNode; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="display text-[30px] sm:text-[38px]">{title}</h1>
        {sub && <p className="mt-2 max-w-[62ch] text-muted">{sub}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton h-4", className)} aria-hidden />;
}

export function LoadingRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
    </div>
  );
}

export function EmptyState({ title, body, action, icon }: { title: ReactNode; body?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-[18px] border border-dashed border-border bg-surface/60 px-6 py-10">
      <span className="text-muted">{icon ?? <Inbox className="h-5 w-5" aria-hidden />}</span>
      <p className="font-medium">{title}</p>
      {body && <p className="max-w-[56ch] text-[14px] text-muted">{body}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <div role="alert" className="flex items-start gap-3 rounded-[10px] border border-danger/40 bg-danger/5 px-5 py-4">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden />
      <div className="flex-1 text-[14px]">
        <p>{message}</p>
        {onRetry && <Button variant="link" size="sm" className="mt-1" onClick={onRetry}>{t.common.retry}</Button>}
      </div>
    </div>
  );
}

export function Notice({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "accent" | "warn" }) {
  return (
    <div className={cn("rounded-[8px] border px-4 py-3 text-[14px]", tone === "accent" ? "border-accent/60 bg-accent/10" : tone === "warn" ? "border-warn/50 bg-warn/10" : "border-border bg-raised/40")}>
      {children}
    </div>
  );
}

export function Dialog({ open, onOpenChange, title, children, footer, wide }: { open: boolean; onOpenChange: (o: boolean) => void; title: ReactNode; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
        <DialogPrimitive.Content className={cn("fixed left-1/2 top-1/2 z-50 max-h-[88vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[20px] border border-border bg-surface p-6 shadow-[var(--shadow-lift)]", wide ? "max-w-3xl" : "max-w-lg")}>
          <div className="mb-5 flex items-start justify-between gap-4">
            <DialogPrimitive.Title className="text-[17px] font-semibold">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close className="rounded p-1 text-muted hover:text-fg" aria-label="Close"><X className="h-4 w-4" /></DialogPrimitive.Close>
          </div>
          <DialogPrimitive.Description className="sr-only">{typeof title === "string" ? title : ""}</DialogPrimitive.Description>
          {children}
          {footer && <div className="mt-6 flex justify-end gap-2">{footer}</div>}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/** Confirmation for destructive / irreversible actions. */
export function Confirm({ trigger, title, body, confirmLabel, onConfirm, danger }: { trigger: ReactNode; title: string; body?: ReactNode; confirmLabel: string; onConfirm: () => Promise<unknown> | void; danger?: boolean }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  return (
    <AlertDialog.Root open={open} onOpenChange={setOpen}>
      <AlertDialog.Trigger asChild>{trigger}</AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
        <AlertDialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-[20px] border border-border bg-surface p-6 shadow-[var(--shadow-lift)]">
          <AlertDialog.Title className="text-[17px] font-semibold">{title}</AlertDialog.Title>
          {body && <AlertDialog.Description className="mt-2 text-[14px] text-muted">{body}</AlertDialog.Description>}
          <div className="mt-6 flex justify-end gap-2">
            <AlertDialog.Cancel asChild><Button variant="ghost">{t.common.cancel}</Button></AlertDialog.Cancel>
            <Button variant={danger ? "danger" : "primary"} loading={busy} onClick={async () => { setBusy(true); try { await onConfirm(); setOpen(false); } finally { setBusy(false); } }}>
              {confirmLabel}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}

export function Switch({ checked, onCheckedChange, label, disabled }: { checked: boolean; onCheckedChange: (v: boolean) => void; label: ReactNode; disabled?: boolean }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 py-1.5 text-[14px]">
      <span>{label}</span>
      <SwitchPrimitive.Root checked={checked} onCheckedChange={onCheckedChange} disabled={disabled}
        className="relative h-[22px] w-[38px] shrink-0 rounded-full border border-border bg-switch transition-colors data-[state=checked]:border-accent data-[state=checked]:bg-accent disabled:opacity-50">
        <SwitchPrimitive.Thumb className="block h-4 w-4 translate-x-[2px] rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-[18px] data-[state=checked]:bg-white" />
      </SwitchPrimitive.Root>
    </label>
  );
}

export const Tabs = TabsPrimitive.Root;
export const TabsContent = TabsPrimitive.Content;
export function TabsList({ items }: { items: { value: string; label: ReactNode }[] }) {
  return (
    <TabsPrimitive.List className="mb-6 flex gap-1 overflow-x-auto border-b border-border">
      {items.map((i) => (
        <TabsPrimitive.Trigger key={i.value} value={i.value}
          className="-mb-px whitespace-nowrap border-b-2 border-transparent px-3 py-2.5 text-[14px] text-muted transition-colors hover:text-fg data-[state=active]:border-accent data-[state=active]:text-fg">
          {i.label}
        </TabsPrimitive.Trigger>
      ))}
    </TabsPrimitive.List>
  );
}

export function Stat({ label, value, sub, accent, icon, tint = 0, href }: { label: ReactNode; value: ReactNode; sub?: ReactNode; accent?: boolean; icon?: ReactNode; tint?: number; href?: string }) {
  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] leading-snug text-muted">{label}</p>
        {icon && <span className={cn("grid h-9 w-9 shrink-0 place-items-center rounded-full [&>svg]:h-[18px] [&>svg]:w-[18px]", accent ? "bg-accent text-accent-fg" : "text-accent")} style={accent ? undefined : { background: `var(--tint-${tint})` }}>{icon}</span>}
      </div>
      <p className="mt-2 text-[28px] font-semibold leading-none tabular-nums tracking-tight">{value}</p>
      {sub && <p className="mt-1.5 text-[12.5px] text-muted">{sub}</p>}
    </>
  );
  const cls = cn("card block px-5 py-4", accent && "border-accent/50 bg-soft-2", href && "card-hover");
  return href ? <a href={href} className={cls}>{inner}</a> : <div className={cls}>{inner}</div>;
}

export function Table({ head, children, empty }: { head: ReactNode[]; children: ReactNode; empty?: boolean }) {
  return (
    <div className="overflow-x-auto rounded-[16px] border border-border bg-surface shadow-[var(--shadow-soft)]">
      <table className="w-full min-w-[640px] text-left text-[14px]">
        <thead className="border-b border-border bg-raised/30 text-[12.5px] text-muted">
          <tr>{head.map((h, i) => <th key={i} className="px-4 py-2.5 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-border">{children}</tbody>
      </table>
      {empty && <p className="px-4 py-8 text-center text-[14px] text-muted">—</p>}
    </div>
  );
}

export function Pager({ page, total, size, onPage }: { page: number; total: number; size: number; onPage: (p: number) => void }) {
  const { t } = useI18n();
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <div className="mt-4 flex items-center justify-end gap-2 text-[13px]">
      <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>{t.common.prev}</Button>
      <span className="px-2 text-muted tabular-nums">{page} / {pages}</span>
      <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>{t.common.next}</Button>
    </div>
  );
}
