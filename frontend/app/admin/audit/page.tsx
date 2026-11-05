"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { ErrorState, LoadingRows, PageHeader, Table } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";

type Log = { id: number; action: string; actor_id: number | null; actor_type: string; entity_type: string | null; entity_id: string | null; ip: string | null; success: boolean; data: Record<string, unknown>; created_at: string };

export default function Audit() {
  const { t, locale } = useI18n();
  const [action, setAction] = useState("");
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const q = useQuery({ queryKey: ["audit", filter, page], queryFn: () => api<{ items: Log[] }>(`/admin/audit-logs?page=${page}${filter ? `&action=${encodeURIComponent(filter)}` : ""}`) });
  return (
    <>
      <PageHeader title={t.admin.audit} sub="Append-only: entries cannot be edited or deleted, including by administrators." />
      <form className="mb-4 max-w-sm" onSubmit={(e) => { e.preventDefault(); setFilter(action); setPage(1); }}><Input placeholder="auth., payment., order., ai." value={action} onChange={(e) => setAction(e.target.value)} aria-label={t.admin.action} /></form>
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} /> : (
        <Table head={[t.common.date, t.admin.action, t.admin.actor, t.admin.entity, "IP", ""]}>
          {q.data?.items.map((l) => (
            <tr key={l.id} className="align-top">
              <td className="whitespace-nowrap px-4 py-2.5 text-[13px] tabular-nums">{date(l.created_at, locale, true)}</td>
              <td className={`px-4 py-2.5 ${l.success ? "" : "text-danger"}`}>{l.action}</td>
              <td className="px-4 py-2.5 text-[13px]">{l.actor_type}{l.actor_id ? ` #${l.actor_id}` : ""}</td>
              <td className="px-4 py-2.5 text-[13px]">{l.entity_type ? `${l.entity_type} #${l.entity_id}` : "—"}</td>
              <td className="px-4 py-2.5 text-[13px]">{l.ip ?? "—"}</td>
              <td className="max-w-[320px] px-4 py-2.5"><code className="block truncate text-[12px] text-muted" title={JSON.stringify(l.data)}>{JSON.stringify(l.data)}</code></td>
            </tr>
          ))}
        </Table>
      )}
      <div className="mt-4 flex gap-2">
        <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t.common.prev}</Button>
        <Button size="sm" variant="outline" disabled={(q.data?.items.length ?? 0) < 50} onClick={() => setPage(page + 1)}>{t.common.next}</Button>
      </div>
    </>
  );
}
