"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Confirm, Dialog, PageHeader, Panel, Switch, Tabs, TabsContent, TabsList } from "@/components/ui/misc";
import { TInput, emptyT } from "@/features/admin/translatable";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { Translatable } from "@/types/api";

type Page = { slug: string; title: Translatable; body: Translatable; is_published: boolean; updated_at: string };
type Faq = { id: number; question: Translatable; answer: Translatable; sort_order: number; is_published: boolean };
const SLUGS = ["terms", "privacy", "refund-policy", "service-policy", "about", "ai-notice"];

export default function Content() {
  const { t, locale } = useI18n();
  const { data: me } = useMe();
  const canSettings = !!me?.permissions.includes("settings.manage");
  const pages = useQuery({ queryKey: ["pages"], queryFn: () => api<{ items: Page[] }>("/admin/pages"), enabled: canSettings });
  const faq = useQuery({ queryKey: ["faq-admin"], queryFn: () => api<{ items: Faq[] }>("/admin/faq"), enabled: canSettings });
  const reviews = useQuery({ queryKey: ["reviews"], queryFn: () => api<{ items: { order_id: number; order_number: string; rating: number; text: string; public: boolean; customer_email: string; reviewed_at: string }[] }>("/admin/reviews") });
  const inbox = useQuery({ queryKey: ["inbox"], queryFn: () => api<{ items: { id: number; name: string; email: string; subject: string; message: string; handled_at: string | null; created_at: string }[] }>("/admin/contact-requests") });
  const [page, setPage] = useState<Page | null>(null);
  const [f, setF] = useState<Faq | null>(null);
  const run = async (fn: () => Promise<unknown>, after?: () => void) => { try { await fn(); toast.success(t.common.saved); after?.(); } catch (e) { toast.error(errorMessage(e, t)); } };
  const tabs = [...(canSettings ? [{ value: "pages", label: t.admin.pages }, { value: "faq", label: t.admin.faqItems }] : []), { value: "reviews", label: t.admin.reviews }, { value: "inbox", label: t.admin.inbox }];
  return (
    <>
      <PageHeader title={t.admin.content} />
      <Tabs defaultValue={tabs[0]!.value}>
        <TabsList items={tabs} />
        <TabsContent value="pages">
          <p className="mb-4 max-w-[70ch] text-[14px] text-muted">Write and approve legal texts yourself (or with a lawyer). Markdown is supported; raw HTML is not rendered.</p>
          <ul className="divide-y divide-border rounded-[10px] border border-border">
            {SLUGS.map((slug) => {
              const p = pages.data?.items.find((x) => x.slug === slug);
              return (
                <li key={slug} className="flex items-center justify-between gap-3 px-5 py-3">
                  <span><span className="font-medium">{slug}</span> <span className={p?.is_published ? "text-ok" : "text-muted"}>· {p?.is_published ? t.admin.publish : "draft"}</span></span>
                  <Button size="sm" variant="outline" onClick={() => setPage(p ?? { slug, title: emptyT(), body: emptyT(), is_published: false, updated_at: "" })}>{t.common.edit}</Button>
                </li>
              );
            })}
          </ul>
        </TabsContent>
        <TabsContent value="faq">
          <Button className="mb-4" size="sm" onClick={() => setF({ id: 0, question: emptyT(), answer: emptyT(), sort_order: (faq.data?.items.length ?? 0), is_published: true })}>{t.admin.addFaq}</Button>
          <ul className="divide-y divide-border rounded-[10px] border border-border">
            {faq.data?.items.map((x) => (
              <li key={x.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <span>{x.question[locale] || x.question.en}{!x.is_published && <span className="text-muted"> · draft</span>}</span>
                <span className="flex gap-1">
                  <Button size="sm" variant="ghost" onClick={() => setF(x)}>{t.common.edit}</Button>
                  <Confirm danger title={t.common.delete} confirmLabel={t.common.delete} onConfirm={() => run(() => api(`/admin/faq/${x.id}`, { method: "DELETE" }), () => faq.refetch())} trigger={<Button size="sm" variant="ghost">{t.common.delete}</Button>} />
                </span>
              </li>
            ))}
          </ul>
        </TabsContent>
        <TabsContent value="reviews">
          <ul className="space-y-3">
            {reviews.data?.items.length === 0 && <p className="text-muted">{t.common.empty}</p>}
            {reviews.data?.items.map((r) => (
              <li key={r.order_id}><Panel>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><p className="text-accent">{"★".repeat(r.rating)}</p><p className="mt-1">{r.text}</p><p className="mt-1 text-[12.5px] text-muted"><Link href={`/admin/orders/${r.order_id}`} className="hover:underline">#{r.order_number}</Link> · {r.customer_email} · {date(r.reviewed_at, locale)}</p></div>
                  <Button size="sm" variant={r.public ? "secondary" : "outline"} onClick={() => run(() => api(`/admin/orders/${r.order_id}/review-visibility`, { body: { public: !r.public } }), () => reviews.refetch())}>{r.public ? t.admin.hide : t.admin.makePublic}</Button>
                </div>
              </Panel></li>
            ))}
          </ul>
        </TabsContent>
        <TabsContent value="inbox">
          <ul className="space-y-3">
            {inbox.data?.items.length === 0 && <p className="text-muted">{t.common.empty}</p>}
            {inbox.data?.items.map((c) => (
              <li key={c.id}><Panel>
                <div className="flex flex-wrap justify-between gap-3">
                  <div className="min-w-0"><p className="font-medium">{c.subject}</p><p className="text-[13px] text-muted">{c.name} · <a className="underline" href={`mailto:${c.email}`}>{c.email}</a> · {date(c.created_at, locale, true)}</p><p className="mt-2 whitespace-pre-line text-[14px]">{c.message}</p></div>
                  {c.handled_at ? <span className="text-[13px] text-ok">✓</span> : <Button size="sm" variant="outline" onClick={() => run(() => api(`/admin/contact-requests/${c.id}/handled`, { method: "POST" }), () => inbox.refetch())}>{t.admin.handled}</Button>}
                </div>
              </Panel></li>
            ))}
          </ul>
        </TabsContent>
      </Tabs>
      {page && (
        <Dialog wide open onOpenChange={(o) => !o && setPage(null)} title={page.slug}
          footer={<Button onClick={() => run(() => api(`/admin/pages/${page.slug}`, { method: "PUT", body: { title: page.title, body: page.body, is_published: page.is_published } }), () => { setPage(null); void pages.refetch(); })}>{t.common.save}</Button>}>
          <div className="space-y-4">
            <TInput label={t.admin.name} value={page.title} onChange={(v) => setPage({ ...page, title: v })} />
            <TInput label="Markdown" value={page.body} onChange={(v) => setPage({ ...page, body: v })} multiline />
            <Switch label={t.admin.publish} checked={page.is_published} onCheckedChange={(v) => setPage({ ...page, is_published: v })} />
          </div>
        </Dialog>
      )}
      {f && (
        <Dialog wide open onOpenChange={(o) => !o && setF(null)} title={t.admin.faqItems}
          footer={<Button onClick={() => run(() => api(f.id ? `/admin/faq/${f.id}` : "/admin/faq", { method: f.id ? "PUT" : "POST", body: { question: f.question, answer: f.answer, sort_order: f.sort_order, is_published: f.is_published } }), () => { setF(null); void faq.refetch(); })}>{t.common.save}</Button>}>
          <div className="space-y-4">
            <TInput label={t.admin.question} value={f.question} onChange={(v) => setF({ ...f, question: v })} />
            <TInput label={t.admin.answer} value={f.answer} onChange={(v) => setF({ ...f, answer: v })} multiline />
            <Input type="number" aria-label="#" value={f.sort_order} onChange={(e) => setF({ ...f, sort_order: Number(e.target.value) })} />
            <Switch label={t.admin.publish} checked={f.is_published} onCheckedChange={(v) => setF({ ...f, is_published: v })} />
          </div>
        </Dialog>
      )}
    </>
  );
}
