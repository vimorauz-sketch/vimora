"use client";

import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { OrderEvent } from "@/types/api";

export function Timeline({ events, staff }: { events: OrderEvent[]; staff?: boolean }) {
  const { t, locale } = useI18n();
  const st = t.status as Record<string, string>;
  return (
    <ol className="relative space-y-5 border-l border-border pl-6">
      {[...events].reverse().map((e) => (
        <li key={e.id} className="relative">
          <span className="absolute -left-[29px] top-1.5 h-2 w-2 rounded-full bg-accent" aria-hidden />
          <p className="text-[12.5px] tabular-nums text-muted">{date(e.created_at, locale, true)}{staff ? ` · ${e.actor_type}${e.customer_visible === false ? " · private" : ""}` : ""}</p>
          <p className="mt-0.5 text-[14.5px]">{e.to_status ? st[e.to_status] ?? e.to_status : e.type.replace(/_/g, " ").toLowerCase()}</p>
          {e.message && <p className="mt-0.5 text-[13.5px] text-muted">{e.message}</p>}
        </li>
      ))}
    </ol>
  );
}
