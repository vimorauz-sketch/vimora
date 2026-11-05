"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, CalendarDays, Check, CircleCheck, Clock3, Lightbulb, Mail, Paperclip } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { FileUploader, Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Checkbox, Field, Input, Textarea } from "@/components/ui/field";
import { PrettySelect } from "@/components/ui/pretty-select";
import { ModeBadge } from "@/components/mode-badge";
import { useMe, useSite } from "@/hooks/queries";
import { AreaPicker } from "@/features/local/area-picker";
import { api, errorMessage } from "@/lib/api";
import { useArea, useAreas } from "@/lib/area";
import { useI18n } from "@/lib/i18n/client";
import type { Attachment, OrderDetail, PriceResult, Service } from "@/types/api";

/** Order form. The price shown comes from the server; the server recomputes it again on submit. */
const MIN_DESC = 10;
type When = "none" | "d1" | "d3" | "d7" | "pick";

type StepKey = "area" | "task" | "handover" | "files" | "review";

function Step({ title, hint, children }: { n?: number; title: string; hint?: string; done?: boolean; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="text-[19px] font-semibold leading-snug text-ink">{title}</h3>
      {hint && <p className="mt-1 text-[13.5px] leading-relaxed text-muted">{hint}</p>}
      <div className="mt-5 space-y-4">{children}</div>
    </section>
  );
}

export function OrderForm({ service }: { service: Service }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const { data: me } = useMe();
  const { data: site } = useSite();
  const p = service.pricing;
  const [files, setFiles] = useState<Attachment[]>([]);
  const [promo, setPromo] = useState("");
  const [appliedPromo, setAppliedPromo] = useState<string | undefined>();
  const { area } = useArea();
  const isLocal = service.mode === "LOCAL";
  const localArea = service.service_area;
  const outsideArea = isLocal && !!area && area !== localArea?.slug;
  const [handover, setHandover] = useState<"PICKUP" | "MEETUP">("PICKUP");
  const [meetPlace, setMeetPlace] = useState("");
  const [meetTime, setMeetTime] = useState("");
  const [meetNote, setMeetNote] = useState("");
  const [areaError, setAreaError] = useState<string | null>(null);
  const optLabel = (o: string) => (t.biz.opt as Record<string, string>)[o] ?? o;
  const [when, setWhen] = useState<When>("none");
  const [resent, setResent] = useState<string | null | false>(false);
  const [cur, setCur] = useState(0);
  const [dir, setDir] = useState<1 | -1>(1);
  const [stepError, setStepError] = useState<string | null>(null);
  const topRef = useRef<HTMLFormElement>(null);
  const steps: StepKey[] = ["area", "task", ...(isLocal && !outsideArea ? (["handover"] as const) : []), "files", "review"];
  const last = steps.length - 1;
  const at: StepKey = steps[Math.min(cur, last)] ?? "review";
  const schema = z.object({
    title: z.string().trim().max(200),
    description: z.string().trim().min(MIN_DESC, t.of.descMin.replace("{n}", String(MIN_DESC))).max(20000),
    quantity: z.coerce.number().int().min(p?.min_quantity ?? 1).max(p?.max_quantity ?? 1000),
    addons: z.array(z.string()),
    deadline: z.string().optional(),
    req: z.record(z.string(), z.string()),
  });
  type F = z.infer<typeof schema>;
  const form = useForm<F>({ resolver: zodResolver(schema) as never, defaultValues: { title: "", description: "", quantity: p?.min_quantity ?? 1, addons: [], req: {} } });
  const qty = form.watch("quantity");
  const addons = form.watch("addons");
  const price = useQuery({
    queryKey: ["price", service.slug, qty, addons, appliedPromo, locale],
    queryFn: () => api<PriceResult>("/catalog/price", { body: { service_slug: service.slug, quantity: Number(qty) || 1, addons, promo_code: appliedPromo, language: locale } }),
    enabled: !!p && p.pricing_type !== "CUSTOM_QUOTE",
    retry: false,
  });

  function deadlineIso(picked?: string): string | undefined {
    const days = { d1: 1, d3: 3, d7: 7 }[when as "d1" | "d3" | "d7"];
    if (days) return new Date(Date.now() + days * 86400_000).toISOString();
    if (when === "pick" && picked) { const d = new Date(`${picked}T18:00:00`); return Number.isNaN(d.getTime()) ? undefined : d.toISOString(); }
    return undefined;
  }

  async function submit(v: F) {
    for (const f of service.required_fields ?? []) {
      if (f.required && !v.req[f.key]?.trim()) { form.setError(`req.${f.key}` as never, { message: t.common.required }); return; }
    }
    if (!area) { setAreaError(t.biz.chooseArea); setCur(0); return; }
    if (outsideArea) return;
    if (service.requires_file && files.length === 0) { toast.error(t.biz.requiresFile); return; }
    if (isLocal && handover === "MEETUP" && (!meetPlace.trim() || !meetTime)) { toast.error(t.common.required); return; }
    try {
      const o = await api<OrderDetail>("/orders", {
        body: { service_slug: service.slug, title: v.title.trim() || service.name, description: v.description, quantity: v.quantity, addons: v.addons, requirements: v.req, promo_code: appliedPromo,
          attachment_ids: files.map((f) => f.id), deadline: deadlineIso(v.deadline), preferred_language: locale,
          area, handover_method: isLocal ? handover : undefined,
          meetup_place: isLocal && handover === "MEETUP" ? meetPlace.trim() : undefined,
          meetup_time: isLocal && handover === "MEETUP" && meetTime ? new Date(meetTime).toISOString() : undefined,
          meetup_note: isLocal && handover === "MEETUP" ? meetNote.trim() || undefined : undefined },
      });
      toast.success(t.services.orderPlaced);
      router.push(`/dashboard/orders/${o.id}`);
    } catch (e) {
      toast.error(errorMessage(e, t));
    }
  }

  const areaName = useAreaName(area);
  useEffect(() => {
    const el = topRef.current;
    if (!el || cur === 0) return;
    const top = el.getBoundingClientRect().top;
    if (top < 0) window.scrollTo({ top: window.scrollY + top - 96, behavior: "smooth" });
  }, [cur]);
  if (!me) {
    return (
      <div className="card overflow-hidden">
        <div className="bg-[radial-gradient(120%_120%_at_0%_0%,var(--glow),transparent)] p-6">
          <h2 className="display text-[24px]">{t.of.loginTitle}</h2>
          <p className="mt-2 text-[14px] text-muted">{t.of.loginBody}</p>
          <p className="mt-4 rounded-[12px] bg-surface/80 px-4 py-3 text-[13.5px]">{p?.pricing_type === "CUSTOM_QUOTE" ? t.services.quoteNote : t.services.startingNote}</p>
        </div>
        <div className="flex flex-col gap-2 p-6 pt-4 sm:flex-row">
          <Button asChild className="flex-1" size="lg"><Link href={`/login?next=/services/${service.slug}`}>{t.services.signInToOrder}</Link></Button>
          <Button asChild variant="outline" className="flex-1" size="lg"><Link href={`/register?next=/services/${service.slug}`}>{t.of.register}</Link></Button>
        </div>
      </div>
    );
  }
  const errs = form.formState.errors;
  async function checkStep(k: StepKey): Promise<boolean> {
    if (k === "area") {
      if (!area) { setAreaError(t.biz.chooseArea); return false; }
      return !outsideArea;
    }
    if (k === "task") {
      const ok = await form.trigger(["title", "description", "quantity"]);
      let reqOk = true;
      for (const f of service.required_fields ?? []) {
        if (f.required && !form.getValues(`req.${f.key}`)?.trim()) { form.setError(`req.${f.key}` as never, { message: t.common.required }); reqOk = false; }
      }
      return ok && reqOk;
    }
    if (k === "handover") return handover === "PICKUP" || (!!meetPlace.trim() && !!meetTime);
    if (k === "files") return !(service.requires_file && files.length === 0);
    return true;
  }
  async function go(to: number) {
    if (to > cur) {
      for (let i = cur; i < to; i++) {
        const k = steps[i]!; if (!(await checkStep(k))) { setCur(i); setStepError(k === "files" ? t.biz.requiresFile : t.of.fixStep); return; }
      }
    }
    setStepError(null);
    setDir(to > cur ? 1 : -1);
    setCur(Math.max(0, Math.min(to, last)));
  }
  const desc = form.watch("description") ?? "";
  const descOk = desc.trim().length >= MIN_DESC;
  const reqFields = service.required_fields ?? [];
  return (
    <form ref={topRef} onSubmit={(e) => { e.preventDefault(); if (cur < last) void go(cur + 1); else void form.handleSubmit(submit, () => void go(steps.indexOf("task")))(); }}
      className="card scroll-mt-24 overflow-hidden" noValidate>
      <div className="border-b border-border bg-[radial-gradient(120%_140%_at_0%_0%,var(--glow),transparent)] px-6 pb-5 pt-6">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="display text-[26px]">{t.of.title}</h2>
          <span className="shrink-0 text-[12.5px] font-medium tabular-nums text-muted" aria-live="polite">{t.of.stepOf.replace("{n}", String(cur + 1)).replace("{total}", String(steps.length))}</span>
        </div>
        <ol className="mt-4 flex gap-1.5" aria-label={t.of.title}>
          {steps.map((k, i) => (
            <li key={k} className="flex-1">
              <button type="button" onClick={() => void go(i)} aria-current={i === cur ? "step" : undefined} className="group block w-full text-left">
                <span className="block h-1.5 overflow-hidden rounded-full bg-raised">
                  <span className={`block h-full rounded-full transition-all duration-500 ${i < cur ? "w-full bg-ok" : i === cur ? "w-full bg-accent" : "w-0 bg-accent"}`} />
                </span>
                <span className={`mt-1.5 flex items-center gap-1 truncate text-[11.5px] transition-colors ${i === cur ? "font-semibold text-ink" : i < cur ? "text-ok" : "text-muted group-hover:text-fg"}`}>
                  {i < cur && <Check className="h-3 w-3 shrink-0" aria-hidden />}{t.of.short[k]}
                </span>
              </button>
            </li>
          ))}
        </ol>
      </div>
      <div className="px-6 pt-6">
        {!me.user.email_verified && (
          <div className="mb-6 flex gap-3 rounded-[16px] border border-warn/30 bg-tint-5 p-4">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-surface text-warn"><Mail className="h-4 w-4" aria-hidden /></span>
            <div className="min-w-0 text-[13.5px]">
              <p className="font-semibold text-ink">{t.of.verifyTitle}</p>
              <p className="mt-0.5 text-muted">{t.of.verifyBody}</p>
              {resent === false ? (
                <button type="button" className="mt-2 font-medium text-accent underline-offset-4 hover:underline"
                  onClick={async () => { const r = await api<{ dev_verify_url?: string }>("/auth/resend-verification", { body: { email: me.user.email } }).catch(() => undefined); setResent(r?.dev_verify_url ?? null); }}>
                  {t.of.resend}
                </button>
              ) : (
                <p className="mt-2 text-ok">{t.of.resent}{resent && <> · <a className="font-medium text-accent underline" href={new URL(resent).pathname + new URL(resent).search}>{t.auth.devVerifyBtn}</a></>}</p>
              )}
            </div>
          </div>
        )}
        <div key={at} className={`min-h-[300px] ${dir === 1 ? "animate-[vimora-step-in_.35s_ease-out]" : "animate-[vimora-step-back_.35s_ease-out]"}`}>

        {at === "area" && (
        <Step n={1} title={t.of.s1} hint={t.of.s1Hint} done={!!area && !outsideArea}>
          <AreaPicker size="lg" onChange={() => setAreaError(null)} />
          {areaError && <p className="text-[12.5px] text-danger">{areaError}</p>}
          {outsideArea && (
            <div role="alert" className="rounded-[14px] border border-warn/40 bg-tint-5 p-4 text-[14px]">
              <p>{t.biz.notHere.replace("{area}", localArea?.name ?? "")}</p>
              <Button asChild variant="outline" size="sm" className="mt-3"><Link href="/services?mode=ONLINE">{t.biz.notHereCta}</Link></Button>
            </div>
          )}
          {service.mode === "REMOTE" && <p className="rounded-[14px] bg-tint-2 px-4 py-3 text-[13px] leading-relaxed">{t.biz.remoteConsent}</p>}
        </Step>
        )}

        {at === "task" && (
        <Step n={2} title={t.of.s2} hint={t.of.s2Hint} done={descOk}>
          <Field label={t.of.nameLabel} optional={t.common.optional} hint={t.of.nameHint}>{(id, d) => <Input id={id} aria-describedby={d} placeholder={t.of.namePh} {...form.register("title")} />}</Field>
          <div>
            <Field label={t.of.descLabel} error={errs.description?.message}>
              {(id) => <Textarea id={id} rows={5} placeholder={t.of.descPh} {...form.register("description")} aria-invalid={!!errs.description} />}
            </Field>
            <p className={`mt-1.5 flex items-center gap-1.5 text-[12px] ${descOk ? "text-ok" : "text-muted"}`} aria-live="polite">
              {descOk ? <CircleCheck className="h-3.5 w-3.5" aria-hidden /> : null}
              {descOk ? t.of.descOk : `${desc.trim().length} / ${MIN_DESC} — ${t.of.descMin.replace("{n}", String(MIN_DESC))}`}
            </p>
          </div>
          <div className="rounded-[14px] bg-raised/60 px-4 py-3">
            <p className="flex items-center gap-2 text-[12.5px] font-semibold text-ink"><Lightbulb className="h-3.5 w-3.5 text-accent" aria-hidden />{t.of.tipsTitle}</p>
            <ul className="mt-1.5 space-y-0.5 text-[12.5px] text-muted">{t.of.tips.map((x) => <li key={x}>• {x}</li>)}</ul>
          </div>
          {p && ["PER_UNIT", "QUANTITY_TIERED", "STARTING_FROM"].includes(p.pricing_type) && p.max_quantity > 1 && (
            <Field label={`${t.services.quantity}${p.unit_label ? ` (${p.unit_label})` : ""}`} error={errs.quantity?.message}>
              {(id) => <Input id={id} type="number" min={p.min_quantity} max={p.max_quantity} {...form.register("quantity")} />}
            </Field>
          )}
          {reqFields.length > 0 && (
            <div className="grid gap-4 rounded-[16px] border border-border p-4 sm:grid-cols-2">
              <p className="text-[12.5px] font-semibold uppercase tracking-wide text-muted sm:col-span-2">{t.of.details}</p>
              {reqFields.map((f) => {
                const err = (errs.req as Record<string, { message?: string }> | undefined)?.[f.key]?.message;
                return (
                  <div key={f.key} className={f.type === "textarea" ? "sm:col-span-2" : ""}>
                    <Field label={f.label} optional={f.required ? undefined : t.common.optional} error={err}>
                      {(id) => f.type === "textarea" ? <Textarea id={id} {...form.register(`req.${f.key}`)} />
                        : f.type === "select" ? (
                          <PrettySelect id={id} value={form.watch(`req.${f.key}`)} placeholder={t.of.choose} aria-label={f.label} aria-invalid={!!err}
                            options={(f.options ?? []).map((o) => ({ value: o, label: optLabel(o) }))}
                            onValueChange={(v) => form.setValue(`req.${f.key}`, v, { shouldValidate: true })} />
                        )
                        : <Input id={id} type={f.type === "number" ? "number" : f.type === "url" ? "url" : "text"} min={f.type === "number" ? 1 : undefined} {...form.register(`req.${f.key}`)} />}
                    </Field>
                  </div>
                );
              })}
            </div>
          )}
          {p && p.addons.length > 0 && (
            <fieldset className="space-y-2">
              <legend className="mb-1 text-[13px] font-medium">{t.services.addons}</legend>
              {p.addons.map((a) => (
                <Checkbox key={a.key} value={a.key} {...form.register("addons")} label={<>{a.label} <span className="text-muted">+<Money minor={a.price_minor} currency={p.currency} /></span></>} />
              ))}
            </fieldset>
          )}
        </Step>
        )}

        {at === "handover" && (
          <Step n={3} title={t.biz.handover} hint={t.biz.cashNote} done={handover === "PICKUP" || (!!meetPlace.trim() && !!meetTime)}>
            <div className="grid gap-2 sm:grid-cols-2">
              {(["PICKUP", "MEETUP"] as const).map((m) => (
                <label key={m} className={`flex cursor-pointer gap-3 rounded-[16px] border p-4 transition-all ${handover === m ? "border-accent bg-tint-0/60 shadow-[var(--shadow-soft)]" : "border-border hover:border-accent/50"}`}>
                  <input type="radio" name="handover" value={m} checked={handover === m} onChange={() => setHandover(m)} className="mt-1 accent-[var(--accent)]" />
                  <span><span className="block text-[14px] font-medium">{m === "PICKUP" ? t.biz.pickup : t.biz.meetup}</span>
                    <span className="mt-0.5 block text-[12.5px] leading-relaxed text-muted">{m === "PICKUP" ? t.biz.pickupHint : t.biz.meetupHint}</span></span>
                </label>
              ))}
            </div>
            {handover === "MEETUP" && (
              <div className="grid gap-3 rounded-[16px] bg-raised/50 p-4 sm:grid-cols-2">
                <div className="sm:col-span-2"><Field label={t.biz.meetupPlace}>{(id) => <Input id={id} value={meetPlace} onChange={(e) => setMeetPlace(e.target.value)} maxLength={300} placeholder={t.biz.meetupPlacePh} />}</Field></div>
                <Field label={t.biz.meetupTime}>{(id) => <Input id={id} type="datetime-local" value={meetTime} onChange={(e) => setMeetTime(e.target.value)} min={new Date(Date.now() + 3600_000).toISOString().slice(0, 16)} />}</Field>
                <Field label={t.biz.meetupNote} optional={t.common.optional}>{(id) => <Input id={id} value={meetNote} onChange={(e) => setMeetNote(e.target.value)} maxLength={1000} />}</Field>
              </div>
            )}
          </Step>
        )}

        {at === "files" && (
        <Step n={3} title={t.of.s3} hint={t.of.s3Hint} done={files.length > 0 || when !== "none"}>
          {service.allows_attachments && (
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-[13px] font-medium"><Paperclip className="h-3.5 w-3.5 text-muted" aria-hidden />{t.services.attachments}{service.requires_file && <span className="text-danger"> *</span>}</p>
              <FileUploader value={files} onChange={setFiles} maxMb={site?.["uploads.max_mb"] ?? 25} />
              <p className="mt-1.5 text-[12px] text-muted">{t.services.attachmentsHint.replace("{mb}", String(site?.["uploads.max_mb"] ?? 25))}</p>
            </div>
          )}
          <div>
            <p className="mb-2 flex items-center gap-1.5 text-[13px] font-medium"><Clock3 className="h-3.5 w-3.5 text-muted" aria-hidden />{t.of.when}</p>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t.of.when}>
              {(Object.keys(t.of.whenOpts) as When[]).map((k) => (
                <button key={k} type="button" role="radio" aria-checked={when === k} onClick={() => setWhen(k)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-[13px] transition-all ${when === k ? "border-accent bg-accent text-accent-fg shadow-[var(--shadow-soft)]" : "border-border bg-surface hover:border-accent/50"}`}>
                  {k === "pick" && <CalendarDays className="h-3.5 w-3.5" aria-hidden />}{t.of.whenOpts[k]}
                </button>
              ))}
            </div>
            {when === "pick" && <Input type="date" className="mt-3 max-w-[220px]" aria-label={t.of.whenOpts.pick} min={new Date(Date.now() + 86400_000).toISOString().slice(0, 10)} {...form.register("deadline")} />}
            <p className="mt-2 text-[12px] text-muted">{t.of.whenHint}</p>
          </div>
          {p && p.pricing_type !== "CUSTOM_QUOTE" && (
            <div className="flex gap-2">
              <Input placeholder={t.services.promo} value={promo} onChange={(e) => setPromo(e.target.value.toUpperCase())} maxLength={40} aria-label={t.services.promo} />
              <Button type="button" variant="outline" onClick={() => setAppliedPromo(promo || undefined)}>{t.services.promoApply}</Button>
            </div>
          )}
        </Step>
        )}

        {at === "review" && (
        <Step n={4} title={t.of.s4}>
          <dl className="divide-y divide-border rounded-[16px] border border-border text-[13.5px]">
            <div className="flex items-center justify-between gap-3 px-4 py-2.5"><dt className="text-muted">{t.of.summary.service}</dt><dd className="truncate text-right font-medium">{service.name}</dd></div>
            <div className="flex items-center justify-between gap-3 px-4 py-2.5"><dt className="text-muted">{t.of.summary.type}</dt><dd><ModeBadge s={service} t={t} /></dd></div>
            <div className="flex items-center justify-between gap-3 px-4 py-2.5"><dt className="text-muted">{t.of.summary.area}</dt><dd className="font-medium">{areaName ?? <span className="text-muted">{t.of.notChosen}</span>}</dd></div>
            <div className="px-4 py-2.5" aria-live="polite">
              {p?.pricing_type === "CUSTOM_QUOTE" || !p ? (
                <div className="flex items-center justify-between gap-3"><dt className="text-muted">{t.of.summary.price}</dt><dd className="text-right font-medium">{t.services.customQuote}</dd></div>
              ) : price.isLoading ? <p className="text-muted">{t.services.calculating}</p>
                : price.error ? <p className="text-danger">{errorMessage(price.error, t)}</p>
                : price.data ? (
                  <div className="space-y-1">
                    {price.data.discount_minor > 0 && <div className="flex justify-between"><dt className="text-muted">{t.dash.discount}</dt><dd>−<Money minor={price.data.discount_minor} currency={price.data.currency} /></dd></div>}
                    <div className="flex justify-between text-[15px] font-semibold"><dt>{t.common.total}</dt><dd><Money minor={price.data.total_minor} currency={price.data.currency} /></dd></div>
                    <div className="flex justify-between"><dt className="text-muted">{t.services.depositShare}</dt><dd><Money minor={price.data.deposit_minor} currency={price.data.currency} /></dd></div>
                    <div className="flex justify-between"><dt className="text-muted">{t.services.payOnDelivery}</dt><dd><Money minor={price.data.remaining_minor} currency={price.data.currency} /></dd></div>
                  </div>
                ) : null}
            </div>
          </dl>
          <div className="rounded-[16px] bg-raised/60 p-4">
            <p className="text-[12.5px] font-semibold uppercase tracking-wide text-muted">{t.of.next}</p>
            <ol className="mt-2.5 space-y-2">
              {t.of.flow.map((x, i) => (
                <li key={x} className="flex items-start gap-2.5 text-[13px]"><span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-surface text-[11px] font-semibold text-accent">{i + 1}</span>{x}</li>
              ))}
            </ol>
          </div>
          <p className="text-[12px] text-muted">{t.custom.aiNotice} <Link href="/ai-notice" className="underline">{t.pages.aiNotice}</Link></p>
        </Step>
        )}
        </div>
      </div>
      <div className="sticky bottom-0 mt-6 border-t border-border bg-surface/95 px-6 py-4 backdrop-blur">
        {stepError && <p role="alert" className="mb-3 text-[12.5px] text-danger">{stepError}</p>}
        <div className="flex items-center gap-2">
          {cur > 0 && (
            <Button type="button" variant="outline" size="lg" onClick={() => void go(cur - 1)} className="px-5">
              <ArrowLeft className="h-4 w-4" aria-hidden />{t.of.goBack}
            </Button>
          )}
          {cur < last ? (
            <Button type="submit" size="lg" className="flex-1" disabled={at === "area" && outsideArea}>
              {t.of.goNext}<ArrowRight className="h-4 w-4" aria-hidden />
            </Button>
          ) : (
            <Button type="submit" size="lg" className="flex-1" loading={form.formState.isSubmitting} disabled={!me.user.email_verified || outsideArea}>{t.services.placeOrder}</Button>
          )}
        </div>
      </div>
    </form>
  );
}

function useAreaName(slug: string | null): string | null {
  const { locale } = useI18n();
  const areas = useAreas(locale);
  return areas.data?.items.find((a) => a.slug === slug)?.name ?? null;
}
