"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { FileChip, FileUploader } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/field";
import { ErrorState, LoadingRows } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { cn, date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Attachment, Message } from "@/types/api";

/** Order conversation. Uses a WebSocket for live updates when available, with polling as a fallback. */
export function MessageThread({ orderId, staff }: { orderId: number; staff?: boolean }) {
  const { t, locale } = useI18n();
  const qc = useQueryClient();
  const base = staff ? `/admin/orders/${orderId}/messages` : `/orders/${orderId}/messages`;
  const key = ["messages", orderId, staff];
  const [live, setLive] = useState(false);
  const q = useQuery({ queryKey: key, queryFn: () => api<{ items: Message[] }>(base), refetchInterval: live ? false : 15_000 });
  const [body, setBody] = useState("");
  const [files, setFiles] = useState<Attachment[]>([]);
  const [sending, setSending] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${proto}://${window.location.host}/api/v1/ws/orders/${orderId}`);
      ws.onopen = () => setLive(true);
      ws.onclose = () => setLive(false);
      ws.onmessage = (ev) => {
        try { if (JSON.parse(ev.data).type === "message") void qc.invalidateQueries({ queryKey: key }); } catch { /* ignore */ }
      };
    } catch { setLive(false); }
    return () => ws?.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [q.data?.items.length]);

  async function send() {
    if (!body.trim() && !files.length) return;
    setSending(true);
    try {
      await api(base, { body: { body, attachment_ids: files.map((f) => f.id) } });
      setBody(""); setFiles([]);
      await qc.invalidateQueries({ queryKey: key });
    } catch (e) { toast.error(errorMessage(e, t)); } finally { setSending(false); }
  }
  if (q.isLoading) return <LoadingRows rows={3} />;
  if (q.error) return <ErrorState message={errorMessage(q.error, t)} onRetry={() => q.refetch()} />;
  return (
    <div>
      <div className="max-h-[520px] space-y-4 overflow-y-auto pr-1" aria-live="polite">
        {q.data?.items.length === 0 && <p className="text-muted">{t.dash.noMessages}</p>}
        {q.data?.items.map((m) => {
          const mine = staff ? m.sender_is_staff : !m.sender_is_staff;
          return (
            <div key={m.id} className={cn("max-w-[80%]", mine && "ml-auto")}>
              <p className={cn("mb-1 text-[12px] text-muted", mine && "text-right")}>{mine ? t.dash.you : m.sender_is_staff ? t.dash.staff : m.sender_name} · {date(m.created_at, locale, true)}</p>
              <div className={cn("rounded-[10px] px-4 py-2.5 text-[14.5px]", mine ? "bg-raised" : "border border-border")}>
                {m.body && <p className="whitespace-pre-wrap break-words">{m.body}</p>}
                {m.attachments.length > 0 && <div className="mt-2 space-y-1.5">{m.attachments.map((a) => <FileChip key={a.id} file={a} />)}</div>}
              </div>
            </div>
          );
        })}
        <div ref={end} />
      </div>
      <div className="mt-5 rounded-[10px] border border-border p-2">
        <Textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder={t.dash.messagePh} maxLength={8000} rows={2} aria-label={t.dash.messagePh}
          className="min-h-[60px] border-0 bg-transparent" onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void send(); }} />
        {files.length > 0 && <div className="px-2 pb-2"><div className="grid gap-2 sm:grid-cols-2">{files.map((f) => <FileChip key={f.id} file={f} onRemove={() => setFiles(files.filter((x) => x.id !== f.id))} />)}</div></div>}
        <div className="flex items-center justify-between">
          <FileUploader value={[]} onChange={(v) => setFiles([...files, ...v])} purpose="MESSAGE" compact />
          <Button size="sm" onClick={send} loading={sending} disabled={!body.trim() && !files.length}><Send className="h-3.5 w-3.5" />{t.common.send}</Button>
        </div>
      </div>
    </div>
  );
}
