"use client";

import { MapPin } from "lucide-react";
import Link from "next/link";
import { Money, StageRail, StatusBadge } from "@/components/domain";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { OrderSummary } from "@/types/api";

export function OrderRows({ items, base = "/dashboard/orders", staff }: { items: OrderSummary[]; base?: string; staff?: boolean }) {
  const { locale, t } = useI18n();
  return (
    <ul className="divide-y divide-border rounded-[10px] border border-border">
      {items.map((o) => (
        <li key={o.id}>
          <Link href={`${base}/${o.id}`} className="grid gap-3 px-5 py-4 transition-colors hover:bg-surface md:grid-cols-[1fr_200px_160px] md:items-center">
            <div className="min-w-0">
              <p className="text-[12.5px] tabular-nums text-muted">#{o.order_number} · {date(o.created_at, locale)}{staff && o.customer_email ? ` · ${o.customer_email}` : ""}</p>
              <p className="mt-0.5 truncate font-medium">{o.title}</p>
              {o.service_name && <p className="truncate text-[13px] text-muted">{o.service_name}</p>}
              {o.is_local && o.handover_method && (
                <p className="mt-1.5 inline-flex items-center gap-1.5 rounded-full bg-tint-0 px-2.5 py-0.5 text-[12px] font-medium text-accent">
                  <MapPin className="h-3 w-3" aria-hidden />{t.biz.h.method[o.handover_method]}{o.handover_status ? ` · ${(staff ? t.biz.h.statusAdmin : t.biz.h.status)[o.handover_status]}` : ""}
                </p>
              )}
            </div>
            <div className="space-y-2"><StatusBadge status={o.status} staff={staff} /><StageRail status={o.status} compact /></div>
            <div className="text-[14px] md:text-right">
              {o.total_minor > 0 ? <Money minor={o.total_minor} currency={o.currency} className="font-medium" /> : <span className="text-muted">—</span>}
              {o.total_minor > 0 && o.remaining_minor > 0 && o.paid_minor > 0 && <p className="text-[12.5px] text-muted">−<Money minor={o.paid_minor} currency={o.currency} /></p>}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
