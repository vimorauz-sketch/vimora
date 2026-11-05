"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRows, PageHeader } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { cn, date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Notification } from "@/types/api";

export default function NotificationsPage() {
  const { t, locale } = useI18n();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["notifications"], queryFn: () => api<{ items: Notification[]; unread: number }>("/account/notifications") });
  async function readAll() { await api("/account/notifications/read-all", { method: "POST" }); void qc.invalidateQueries({ queryKey: ["notifications"] }); void qc.invalidateQueries({ queryKey: ["notif-count"] }); }
  return (
    <>
      <PageHeader title={t.dash.notifications} actions={q.data?.unread ? <Button variant="outline" size="sm" onClick={readAll}>{t.dash.markAllRead}</Button> : undefined} />
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} /> : !q.data?.items.length ? <EmptyState title={t.dash.noNotifications} /> : (
        <ul className="divide-y divide-border rounded-[10px] border border-border">
          {q.data.items.map((n) => (
            <li key={n.id} className={cn("px-5 py-4", !n.read_at && "bg-surface")}>
              <div className="flex items-start gap-3">
                <span className={cn("mt-2 h-1.5 w-1.5 shrink-0 rounded-full", n.read_at ? "bg-transparent" : "bg-accent")} aria-hidden />
                <div className="min-w-0 flex-1">
                  {n.link ? <Link href={n.link} className="font-medium hover:underline">{n.title}</Link> : <p className="font-medium">{n.title}</p>}
                  <p className="text-[14px] text-muted">{n.body}</p>
                  <p className="mt-1 text-[12px] text-muted">{date(n.created_at, locale, true)}</p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
