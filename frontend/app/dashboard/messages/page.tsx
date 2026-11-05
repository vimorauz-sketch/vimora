"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { EmptyState, ErrorState, LoadingRows, PageHeader } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";

type Conv = { order_id: number; order_number: string; title: string; unread: number; last_message: string | null; last_message_at: string | null };

export default function MessagesPage() {
  const { t, locale } = useI18n();
  const q = useQuery({ queryKey: ["conversations"], queryFn: () => api<{ items: Conv[] }>("/account/conversations"), refetchInterval: 30_000 });
  return (
    <>
      <PageHeader title={t.dash.messages} />
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} /> : !q.data?.items.length ? <EmptyState title={t.dash.noOrders} /> : (
        <ul className="divide-y divide-border rounded-[10px] border border-border">
          {q.data.items.map((c) => (
            <li key={c.order_id}>
              <Link href={`/dashboard/orders/${c.order_id}?tab=messages`} className="flex items-center gap-4 px-5 py-4 hover:bg-surface">
                <div className="min-w-0 flex-1">
                  <p className="text-[12.5px] text-muted">#{c.order_number}{c.last_message_at ? ` · ${date(c.last_message_at, locale, true)}` : ""}</p>
                  <p className="truncate font-medium">{c.title}</p>
                  <p className="truncate text-[14px] text-muted">{c.last_message ?? t.dash.noMessages}</p>
                </div>
                {c.unread > 0 && <span className="rounded-full bg-accent px-2 text-[12px] font-semibold text-accent-fg">{c.unread}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
