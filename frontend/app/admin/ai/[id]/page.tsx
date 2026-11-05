"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/field";
import { Confirm, Dialog, ErrorState, LoadingRows, Notice, Panel } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { bytes, date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Attachment, Execution } from "@/types/api";

type Detail = Execution & {
  classification: Record<string, unknown> | null; plan: { steps?: { title: string; detail: string }[]; deliverables?: { filename: string; description?: string }[]; risks?: string[] } | null;
  validation_report: { deterministic_checks?: { check: string; passed: boolean; skipped?: boolean; detail: unknown }[]; deterministic_passed?: boolean; requirements_met?: string;
    ai_requirement_review?: { requirements?: { requirement: string; met: boolean; comment: string }[]; issues?: string[] }; note?: string; sandbox?: string } | null;
  order: { id: number; order_number: string; title: string; description: string; requirements: Record<string, string>; status: string };
  steps: { seq: number; stage: string; status: string; summary: string; created_at: string }[];
  reviews: { decision: string; comment: string; created_at: string }[];
  usage: { purpose: string; model: string; input_tokens: number; output_tokens: number; cost_usd: string; success: boolean; error: string | null; latency_ms: number | null }[];
  files: (Attachment & { promoted: boolean })[]; retry_history: Execution[]; suggested_next_steps: string[];
};

/** AI Review Dashboard: everything the owner needs to decide; the AI never approves itself. */
export default function ExecutionReview() {
  const { t, locale } = useI18n();
  const { id } = useParams<{ id: string }>();
  const q = useQuery({ queryKey: ["exec", id], queryFn: () => api<Detail>(`/admin/ai/executions/${id}`), refetchInterval: (s) => (["PENDING", "PLANNING", "RUNNING", "VALIDATING"].includes(s.state.data?.status ?? "") ? 4000 : false) });
  const [selected, setSelected] = useState<number[]>([]);
  const [preview, setPreview] = useState<{ name: string; content: string } | null>(null);
  const [revise, setRevise] = useState(false);
  const [text, setText] = useState("");
  if (q.isLoading) return <LoadingRows rows={8} />;
  if (q.error || !q.data) return <ErrorState message={errorMessage(q.error, t)} />;
  const d = q.data;
  const act = async (path: string, body: unknown = {}) => {
    try { const r = await api<{ execution_id?: number }>(`/admin/ai/executions/${d.id}/${path}`, { body }); toast.success(t.common.saved); if (r?.execution_id) window.location.assign(`/admin/ai/${r.execution_id}`); else void q.refetch(); }
    catch (e) { toast.error(errorMessage(e, t)); }
  };
  const review = d.status === "REVIEW_REQUIRED";
  const running = ["PENDING", "PLANNING", "RUNNING", "VALIDATING"].includes(d.status);
  const rep = d.validation_report;
  return (
    <>
      <Link href={`/admin/orders/${d.order.id}`} className="text-[13px] text-muted hover:text-fg">#{d.order.order_number} · {d.order.title}</Link>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <h1 className="display text-[26px]">{t.admin.review} #{d.id} <span className="text-muted">· {d.attempt}</span></h1>
        <span className={review ? "text-accent" : d.status === "FAILED" ? "text-danger" : "text-muted"}>{d.status}</span>
      </div>
      <p className="mt-1 text-[13.5px] text-muted">{d.capability ?? "auto"} · {t.admin.tokens} {d.input_tokens}/{d.output_tokens} · {t.admin.cost} ${Number(d.cost_usd).toFixed(4)}</p>
      {d.failure_reason && <div className="mt-4"><Notice tone="warn">{d.failure_reason}</Notice></div>}
      <div className="mt-8 grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-6">
          <Panel title={t.dash.order}>
            <p className="whitespace-pre-line text-[14.5px]">{d.order.description}</p>
            {Object.entries(d.order.requirements).map(([k, v]) => <p key={k} className="text-[14px]"><span className="text-muted">{k}:</span> {v}</p>)}
          </Panel>
          {d.files.length > 0 && (
            <Panel title={t.admin.files}>
              <ul className="space-y-2">
                {d.files.map((f) => (
                  <li key={f.id} className="flex items-center gap-3 rounded-[6px] border border-border px-3 py-2 text-[14px]">
                    {review && !f.promoted && <input type="checkbox" aria-label={f.name} className="accent-[var(--accent)]" checked={selected.includes(f.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, f.id] : selected.filter((x) => x !== f.id))} />}
                    <span className="flex-1 truncate">{f.name}</span><span className="text-[12px] text-muted">{bytes(f.size_bytes)}{f.promoted && " · ✓"}</span>
                    <Button size="sm" variant="ghost" onClick={async () => setPreview(await api(`/admin/ai/outputs/${f.id}/preview`))}>{t.admin.preview}</Button>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          {rep && (
            <Panel title={t.admin.validation}>
              <ul className="space-y-1.5 text-[14px]">
                {rep.deterministic_checks?.map((c) => <li key={c.check} className="flex justify-between gap-3"><span>{c.check}</span><span className={c.skipped ? "text-muted" : c.passed ? "text-ok" : "text-danger"}>{c.skipped ? "skipped" : c.passed ? "pass" : "fail"}</span></li>)}
              </ul>
              {rep.ai_requirement_review?.requirements && (
                <div className="mt-4 border-t border-border pt-4">
                  <p className="mb-2 text-[13px] text-warn">{t.admin.selfAssessment} ({rep.requirements_met})</p>
                  <ul className="space-y-1.5 text-[14px]">{rep.ai_requirement_review.requirements.map((r, i) => <li key={i}><span className={r.met ? "text-ok" : "text-danger"}>{r.met ? "✓" : "✗"}</span> {r.requirement}{r.comment && <span className="text-muted"> — {r.comment}</span>}</li>)}</ul>
                  {rep.ai_requirement_review.issues?.length ? <ul className="mt-2 list-disc pl-5 text-[13.5px] text-muted">{rep.ai_requirement_review.issues.map((x) => <li key={x}>{x}</li>)}</ul> : null}
                </div>
              )}
              <p className="mt-3 text-[12.5px] text-muted">Sandbox: {rep.sandbox}</p>
            </Panel>
          )}
          {d.plan?.steps && <Panel title={t.admin.plan}><ol className="list-decimal space-y-2 pl-5 text-[14px]">{d.plan.steps.map((s, i) => <li key={i}><span className="font-medium">{s.title}</span> <span className="text-muted">{s.detail}</span></li>)}</ol></Panel>}
          <Panel title={t.admin.steps}>
            <ol className="space-y-2 text-[14px]">{d.steps.map((s) => <li key={s.seq} className="grid grid-cols-[90px_60px_1fr] gap-3"><span className="text-muted">{s.stage}</span><span className={s.status === "ERROR" ? "text-danger" : "text-ok"}>{s.status}</span><span>{s.summary}</span></li>)}</ol>
            {d.usage.length > 0 && <table className="mt-4 w-full text-[12.5px] text-muted"><tbody>{d.usage.map((u, i) => <tr key={i}><td>{u.purpose}</td><td>{u.model}</td><td className="tabular-nums">{u.input_tokens}/{u.output_tokens}</td><td className="tabular-nums">${Number(u.cost_usd).toFixed(4)}</td><td>{u.latency_ms ?? "—"}ms</td><td className={u.success ? "" : "text-danger"}>{u.error ?? ""}</td></tr>)}</tbody></table>}
          </Panel>
          {d.classification && <Panel title={t.admin.classification}><pre className="overflow-x-auto whitespace-pre-wrap text-[12.5px] text-muted">{JSON.stringify(d.classification, null, 2)}</pre></Panel>}
        </div>
        <aside className="space-y-5">
          <Panel title={t.admin.review}>
            <div className="flex flex-col gap-2">
              {review && <Button disabled={!selected.length} onClick={() => act("approve", { attachment_ids: selected, comment: "" })}>{t.admin.approve} ({selected.length})</Button>}
              {review && <Button variant="outline" onClick={() => setRevise(true)}>{t.admin.revise}</Button>}
              {["FAILED", "REJECTED", "CANCELLED"].includes(d.status) && d.order.status !== "CANCELLED" && <Button variant="outline" onClick={() => act("revise", {})}>{t.admin.retryAi}</Button>}
              {(review || running) && <Button variant="ghost" onClick={() => act("take-over", { comment: "" })}>{t.admin.takeOver}</Button>}
              {review && <Confirm danger title={t.admin.rejectAi} confirmLabel={t.admin.rejectAi} onConfirm={() => act("reject", { comment: "" })} trigger={<Button variant="danger">{t.admin.rejectAi}</Button>} />}
              {running && <Button variant="danger" onClick={() => act("cancel", { comment: "" })}>{t.admin.cancelAi}</Button>}
              {d.status === "APPROVED" && <Button asChild><Link href={`/admin/orders/${d.order.id}`}>{t.admin.completeWork}</Link></Button>}
            </div>
          </Panel>
          {d.suggested_next_steps.length > 0 && <Panel title={t.admin.nextSteps}><ul className="list-disc space-y-1 pl-5 text-[14px]">{d.suggested_next_steps.map((s) => <li key={s}>{s}</li>)}</ul></Panel>}
          <Panel title={t.admin.retryHistory}>
            <ul className="space-y-1.5 text-[13.5px]">{d.retry_history.map((r) => <li key={r.id}><Link href={`/admin/ai/${r.id}`} className={r.id === d.id ? "text-accent" : "hover:underline"}>#{r.attempt} · {r.status} · {date(r.created_at, locale, true)}</Link></li>)}</ul>
          </Panel>
          {d.reviews.length > 0 && <Panel title={t.admin.reviews}><ul className="space-y-1.5 text-[13.5px]">{d.reviews.map((r, i) => <li key={i}>{r.decision} · {date(r.created_at, locale, true)}{r.comment && <span className="block text-muted">{r.comment}</span>}</li>)}</ul></Panel>}
        </aside>
      </div>
      <Dialog wide open={!!preview} onOpenChange={(o) => !o && setPreview(null)} title={preview?.name ?? ""}>
        {/* rendered strictly as text — never as HTML */}
        <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-[6px] bg-bg p-4 text-[13px]">{preview?.content}</pre>
      </Dialog>
      <Dialog open={revise} onOpenChange={setRevise} title={t.admin.revise} footer={<Button onClick={() => act("revise", { instructions: text })} disabled={!text.trim()}>{t.admin.revise}</Button>}>
        <Field label={t.admin.instructions}>{(fid) => <Textarea id={fid} value={text} onChange={(e) => setText(e.target.value)} rows={5} />}</Field>
      </Dialog>
    </>
  );
}
