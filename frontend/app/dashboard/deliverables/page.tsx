"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { FileChip } from "@/components/domain";
import { EmptyState, ErrorState, LoadingRows, PageHeader } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { Deliverable } from "@/types/api";

type Row = Deliverable & { order_id: number; order_number: string; order_title: string };

export default function DeliverablesPage() {
  const { t } = useI18n();
  const q = useQuery({ queryKey: ["my-deliverables"], queryFn: () => api<{ items: Row[] }>("/account/deliverables") });
  const groups = new Map<number, Row[]>();
  q.data?.items.forEach((d) => groups.set(d.order_id, [...(groups.get(d.order_id) ?? []), d]));
  return (
    <>
      <PageHeader title={t.dash.deliverables} />
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} /> : groups.size === 0 ? <EmptyState title={t.dash.noDeliverables} /> : (
        <div className="space-y-8">
          {[...groups.values()].map((rows) => (
            <section key={rows[0]!.order_id}>
              <Link href={`/dashboard/orders/${rows[0]!.order_id}`} className="text-[14px] text-muted hover:text-fg">#{rows[0]!.order_number} · {rows[0]!.order_title}</Link>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">{rows.map((d) => d.attachment && <FileChip key={d.id} file={{ ...d.attachment, name: d.title || d.attachment.name }} />)}</div>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
