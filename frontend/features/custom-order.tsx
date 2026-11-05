"use client";

import { ArrowLeft, ArrowRight, CalendarDays, Check, CircleCheck, Clock3, LayoutGrid, Lightbulb, Mail, Paperclip, Phone, Send, Wallet } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { CategoryIcon } from "@/components/category-icon";
import { FileUploader, Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/field";
import { PrettySelect } from "@/components/ui/pretty-select";
import { useMe, useSite } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { toMinor } from "@/lib/format";
import { LOCALES, LOCALE_LABELS, type Locale } from "@/lib/i18n";
import { useI18n } from "@/lib/i18n/client";
import type { Attachment, Category, OrderDetail } from "@/types/api";

const MIN_DESC = 30;
type StepKey = "task" | "time" | "contact" | "review";
const STEPS: StepKey[] = ["task", "time", "contact", "review"];
type When = "none" | "d1" | "d3" | "d7" | "pick";
type Budget = "none" | "b1" | "b2" | "b3" | "b4" | "own";
const BUDGET_SOM: Record<Exclude<Budget, "none" | "own">, number> = { b1: 200_000, b2: 500_000, b3: 1_000_000, b4: 3_000_000 };

/** Custom request as a short wizard: task → deadline & budget → contact → review. */
export function CustomOrderForm({ categories }: { categories: Category[] }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const { data: me, isLoading } = useMe();
  const { data: site } = useSite();
  const top = useRef<HTMLFormElement>(null);
  const [cur, setCur] = useState(0);
  const [dir, setDir] = useState<1 | -1>(1);
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [resent, setResent] = useState<string | null | false>(false);
  // answers
  const [category, setCategory] = useState("");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState(params.get("d") ?? "");
  const [when, setWhen] = useState<When>("none");
  const [date, setDate] = useState("");
  const [budget, setBudget] = useState<Budget>("none");
  const [ownBudget, setOwnBudget] = useState("");
  const [files, setFiles] = useState<Attachment[]>([]);
  const [language, setLanguage] = useState<Locale>(locale);
  const [phone, setPhone] = useState("");
  const [telegram, setTelegram] = useState("");

  useEffect(() => { if (me?.user.phone && !phone) setPhone(me.user.phone); }, [me?.user.phone]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const el = top.current;
    if (!el || cur === 0) return;
    const y = el.getBoundingClientRect().top;
    if (y < 0) window.scrollTo({ top: window.scrollY + y - 96, behavior: "smooth" });
  }, [cur]);

  const cats = categories.filter((c) => (c.service_count ?? 1) > 0);
  const catName = cats.find((c) => c.slug === category)?.name;
  const budgetMinor = budget === "none" ? undefined : budget === "own" ? toMinor(ownBudget) ?? undefined : BUDGET_SOM[budget] * 100;
  const deadline = (() => {
    const days = { d1: 1, d3: 3, d7: 7 }[when as "d1" | "d3" | "d7"];
    if (days) return new Date(Date.now() + days * 86400_000);
    if (when === "pick" && date) { const d = new Date(`${date}T18:00:00`); return Number.isNaN(d.getTime()) ? undefined : d; }
    return undefined;
  })();
  const descLen = desc.trim().length;

  function check(k: StepKey): boolean {
    const e: Record<string, string> = {};
    if (k === "task") {
      if (title.trim().length < 3) e.title = t.common.required;
      if (descLen < MIN_DESC) e.desc = t.custom.minLength;
    }
    if (k === "time" && budget === "own" && ownBudget && toMinor(ownBudget) === null) e.budget = t.errors.VALIDATION_ERROR;
    if (k === "contact" && telegram && !/^@?[A-Za-z0-9_]{4,32}$/.test(telegram.trim())) e.telegram = t.errors.VALIDATION_ERROR;
    setErr(e);
    return Object.keys(e).length === 0;
  }
  function go(to: number) {
    if (to > cur) for (let i = cur; i < to; i++) { if (!check(STEPS[i]!)) { setDir(1); setCur(i); return; } }
    setErr({});
    setDir(to > cur ? 1 : -1);
    setCur(Math.max(0, Math.min(to, STEPS.length - 1)));
  }
  async function submit() {
    for (let i = 0; i < STEPS.length - 1; i++) if (!check(STEPS[i]!)) { setCur(i); return; }
    setBusy(true);
    try {
      const o = await api<OrderDetail>("/orders", {
        body: { title: title.trim(), description: desc.trim(), category_slug: category || undefined, deadline: deadline?.toISOString(), budget_minor: budgetMinor,
          preferred_language: language, contact_phone: phone.trim() || undefined, contact_telegram: telegram.trim() || undefined, attachment_ids: files.map((f) => f.id) },
      });
      toast.success(t.custom.submitted);
      router.push(`/dashboard/orders/${o.id}`);
    } catch (e) {
      toast.error(errorMessage(e, t));
    } finally { setBusy(false); }
  }

  if (isLoading) return <div className="card h-[520px] animate-pulse" aria-hidden />;
  if (!me) return (
    <div className="card overflow-hidden">
      <div className="bg-[radial-gradient(120%_120%_at_0%_0%,var(--glow),transparent)] p-7">
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-surface text-accent shadow-[var(--shadow-soft)]"><Send className="h-5 w-5" aria-hidden /></span>
        <h2 className="display mt-5 text-[26px]">{t.co.loginTitle}</h2>
        <p className="mt-2 text-[14px] text-muted">{t.co.loginBody}</p>
        <p className="mt-4 rounded-[12px] bg-surface/80 px-4 py-3 text-[13.5px]">{t.co.free}</p>
      </div>
      <div className="flex flex-col gap-2 p-7 pt-4 sm:flex-row">
        <Button asChild size="lg" className="flex-1"><Link href="/login?next=/custom-order">{t.nav.signIn}</Link></Button>
        <Button asChild size="lg" variant="outline" className="flex-1"><Link href="/register?next=/custom-order">{t.nav.signUp}</Link></Button>
      </div>
    </div>
  );

  const at = STEPS[cur]!;
  const last = cur === STEPS.length - 1;
  const chip = (on: boolean) => `inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-[13px] transition-all ${on ? "border-accent bg-accent text-accent-fg shadow-[var(--shadow-soft)]" : "border-border bg-surface hover:border-accent/50"}`;
  const ErrLine = ({ k }: { k: string }) => err[k] ? <p className="mt-1.5 text-[12.5px] text-danger">{err[k]}</p> : null;

  return (
    <form ref={top} noValidate onSubmit={(e) => { e.preventDefault(); if (last) void submit(); else go(cur + 1); }} className="card scroll-mt-24 overflow-hidden">
      <div className="border-b border-border bg-[radial-gradient(120%_140%_at_0%_0%,var(--glow),transparent)] px-6 pb-5 pt-6">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="display text-[26px]">{t.custom.title}</h2>
          <span className="shrink-0 text-[12.5px] font-medium tabular-nums text-muted" aria-live="polite">{t.of.stepOf.replace("{n}", String(cur + 1)).replace("{total}", String(STEPS.length))}</span>
        </div>
        <ol className="mt-4 flex gap-1.5" aria-label={t.custom.title}>
          {STEPS.map((k, i) => (
            <li key={k} className="flex-1">
              <button type="button" onClick={() => go(i)} aria-current={i === cur ? "step" : undefined} className="group block w-full text-left">
                <span className="block h-1.5 overflow-hidden rounded-full bg-raised"><span className={`block h-full rounded-full transition-all duration-500 ${i < cur ? "w-full bg-ok" : i === cur ? "w-full bg-accent" : "w-0"}`} /></span>
                <span className={`mt-1.5 flex items-center gap-1 truncate text-[11.5px] ${i === cur ? "font-semibold text-ink" : i < cur ? "text-ok" : "text-muted group-hover:text-fg"}`}>
                  {i < cur && <Check className="h-3 w-3 shrink-0" aria-hidden />}{t.co.short[k]}
                </span>
              </button>
            </li>
          ))}
        </ol>
      </div>

      <div className="px-6 pt-6">
        {!me.user.email_verified && (
          <div className="mb-6 flex gap-3 rounded-[16px] border border-warn/30 bg-tint-5 p-4 text-[13.5px]">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-surface text-warn"><Mail className="h-4 w-4" aria-hidden /></span>
            <div className="min-w-0">
              <p className="font-semibold text-ink">{t.of.verifyTitle}</p>
              <p className="mt-0.5 text-muted">{t.of.verifyBody}</p>
              {resent === false ? (
                <button type="button" className="mt-2 font-medium text-accent underline-offset-4 hover:underline"
                  onClick={async () => { const r = await api<{ dev_verify_url?: string }>("/auth/resend-verification", { body: { email: me.user.email } }).catch(() => undefined); setResent(r?.dev_verify_url ?? null); }}>{t.of.resend}</button>
              ) : <p className="mt-2 text-ok">{t.of.resent}{resent && <> · <a className="font-medium text-accent underline" href={new URL(resent).pathname + new URL(resent).search}>{t.auth.devVerifyBtn}</a></>}</p>}
            </div>
          </div>
        )}

        <div key={at} className={`min-h-[340px] ${dir === 1 ? "animate-[vimora-step-in_.35s_ease-out]" : "animate-[vimora-step-back_.35s_ease-out]"}`}>
          <h3 className="text-[19px] font-semibold leading-snug text-ink">{t.co[at === "task" ? "s1" : at === "time" ? "s2" : at === "contact" ? "s3" : "s4"]}</h3>
          {at !== "review" && <p className="mt-1 text-[13.5px] leading-relaxed text-muted">{t.co[at === "task" ? "s1Hint" : at === "time" ? "s2Hint" : "s3Hint"]}</p>}

          {at === "task" && (
            <div className="mt-5 space-y-5">
              <div>
                <p className="mb-1.5 text-[13px] font-medium">{t.co.catLabel} <span className="font-normal text-muted">({t.common.optional})</span></p>
                <PrettySelect size="lg" value={category || "any"} onValueChange={(v) => setCategory(v === "any" ? "" : v)} aria-label={t.co.catLabel}
                  options={[{ value: "any", label: t.co.catAny, icon: <span className="grid h-7 w-7 place-items-center rounded-full bg-ink text-ink-fg"><LayoutGrid className="h-3.5 w-3.5" aria-hidden /></span> },
                    ...cats.map((c, i) => ({ value: c.slug, label: c.name, icon: <CategoryIcon name={c.icon} index={i} size="xs" /> }))]} />
              </div>
              <Field label={t.custom.taskTitle} error={err.title}>{(id) => <Input id={id} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} placeholder={t.co.titlePh} aria-invalid={!!err.title} />}</Field>
              <div>
                <Field label={t.custom.description} error={err.desc}>{(id) => <Textarea id={id} rows={6} value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={20000} placeholder={t.custom.descriptionPh} aria-invalid={!!err.desc} />}</Field>
                <p className={`mt-1.5 flex items-center gap-1.5 text-[12px] ${descLen >= MIN_DESC ? "text-ok" : "text-muted"}`} aria-live="polite">
                  {descLen >= MIN_DESC ? <><CircleCheck className="h-3.5 w-3.5" aria-hidden />{t.of.descOk}</> : `${descLen} / ${MIN_DESC} — ${t.co.descMin.replace("{n}", String(MIN_DESC))}`}
                </p>
              </div>
              <div className="rounded-[14px] bg-raised/60 px-4 py-3">
                <p className="flex items-center gap-2 text-[12.5px] font-semibold text-ink"><Lightbulb className="h-3.5 w-3.5 text-accent" aria-hidden />{t.of.tipsTitle}</p>
                <ul className="mt-1.5 space-y-0.5 text-[12.5px] text-muted">{t.co.tips.map((x) => <li key={x}>• {x}</li>)}</ul>
              </div>
            </div>
          )}

          {at === "time" && (
            <div className="mt-5 space-y-6">
              <div>
                <p className="mb-2 flex items-center gap-1.5 text-[13px] font-medium"><Clock3 className="h-3.5 w-3.5 text-muted" aria-hidden />{t.of.when}</p>
                <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t.of.when}>
                  {(Object.keys(t.of.whenOpts) as When[]).map((k) => (
                    <button key={k} type="button" role="radio" aria-checked={when === k} onClick={() => setWhen(k)} className={chip(when === k)}>
                      {k === "pick" && <CalendarDays className="h-3.5 w-3.5" aria-hidden />}{t.of.whenOpts[k]}
                    </button>
                  ))}
                </div>
                {when === "pick" && <Input type="date" className="mt-3 max-w-[220px]" aria-label={t.of.whenOpts.pick} value={date} min={new Date(Date.now() + 86400_000).toISOString().slice(0, 10)} onChange={(e) => setDate(e.target.value)} />}
              </div>
              <div>
                <p className="mb-2 flex items-center gap-1.5 text-[13px] font-medium"><Wallet className="h-3.5 w-3.5 text-muted" aria-hidden />{t.co.budget}</p>
                <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t.co.budget}>
                  {(Object.keys(t.co.budgetOpts) as Budget[]).map((k) => (
                    <button key={k} type="button" role="radio" aria-checked={budget === k} onClick={() => setBudget(k)} className={chip(budget === k)}>
                      {k !== "none" && k !== "own" && "≈ "}{t.co.budgetOpts[k]}
                    </button>
                  ))}
                </div>
                {budget === "own" && <Input className="mt-3 max-w-[260px]" inputMode="numeric" placeholder={t.co.budgetPh} value={ownBudget} onChange={(e) => setOwnBudget(e.target.value)} aria-label={t.co.budgetPh} aria-invalid={!!err.budget} />}
                <ErrLine k="budget" />
              </div>
              <div>
                <p className="mb-1.5 flex items-center gap-1.5 text-[13px] font-medium"><Paperclip className="h-3.5 w-3.5 text-muted" aria-hidden />{t.co.files}</p>
                <FileUploader value={files} onChange={setFiles} maxMb={site?.["uploads.max_mb"] ?? 25} />
                <p className="mt-1.5 text-[12px] text-muted">{t.co.filesHint}</p>
              </div>
            </div>
          )}

          {at === "contact" && (
            <div className="mt-5 space-y-5">
              <div>
                <p className="mb-2 text-[13px] font-medium">{t.co.language}</p>
                <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label={t.co.language}>
                  {LOCALES.map((l) => (
                    <button key={l} type="button" role="radio" aria-checked={language === l} onClick={() => setLanguage(l)}
                      className={`rounded-[14px] border px-3 py-3 text-[14px] font-medium transition-all ${language === l ? "border-accent bg-tint-0/60 shadow-[var(--shadow-soft)] ring-2 ring-accent/15" : "border-border hover:border-accent/40"}`}>{LOCALE_LABELS[l]}</button>
                  ))}
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label={t.co.phone} optional={t.common.optional}>{(id) => (
                  <div className="relative"><Phone className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
                    <Input id={id} type="tel" autoComplete="tel" className="pl-10" placeholder="+998 90 123 45 67" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={40} /></div>)}
                </Field>
                <Field label={t.co.telegram} optional={t.common.optional} error={err.telegram}>{(id) => (
                  <div className="relative"><Send className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
                    <Input id={id} className="pl-10" placeholder="@username" value={telegram} onChange={(e) => setTelegram(e.target.value)} maxLength={33} aria-invalid={!!err.telegram} /></div>)}
                </Field>
              </div>
            </div>
          )}

          {at === "review" && (
            <div className="mt-5 space-y-4">
              <dl className="divide-y divide-border rounded-[16px] border border-border text-[13.5px]">
                {([
                  [t.co.sum.title, title.trim()],
                  [t.co.sum.category, catName ?? t.co.catAny],
                  [t.co.sum.deadline, deadline ? deadline.toLocaleDateString(locale === "en" ? "en-GB" : locale === "ru" ? "ru-RU" : "uz-UZ") : t.of.whenOpts.none],
                  [t.co.sum.budget, budgetMinor ? <Money key="b" minor={budgetMinor} currency="UZS" /> : t.co.notSet],
                  [t.co.sum.files, files.length ? String(files.length) : t.co.notSet],
                  [t.co.sum.contact, [LOCALE_LABELS[language], phone.trim(), telegram.trim()].filter(Boolean).join(" · ")],
                ] as const).map(([k, v]) => (
                  <div key={String(k)} className="flex items-start justify-between gap-4 px-4 py-2.5"><dt className="shrink-0 text-muted">{k}</dt><dd className="min-w-0 break-words text-right font-medium">{v}</dd></div>
                ))}
                <div className="px-4 py-2.5"><dt className="text-muted">{t.custom.description}</dt><dd className="mt-1 line-clamp-4 whitespace-pre-line text-[13px]">{desc.trim()}</dd></div>
              </dl>
              <div className="rounded-[16px] bg-raised/60 p-4">
                <p className="text-[12.5px] font-semibold uppercase tracking-wide text-muted">{t.of.next}</p>
                <ol className="mt-2.5 space-y-2">
                  {t.of.flow.map((x, i) => <li key={x} className="flex items-start gap-2.5 text-[13px]"><span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-surface text-[11px] font-semibold text-accent">{i + 1}</span>{x}</li>)}
                </ol>
              </div>
              <p className="text-[12px] text-muted">{t.custom.aiNotice} <Link href="/ai-notice" className="underline">{t.pages.aiNotice}</Link></p>
            </div>
          )}
        </div>
      </div>

      <div className="sticky bottom-0 mt-6 border-t border-border bg-surface/95 px-6 py-4 backdrop-blur">
        {Object.keys(err).length > 0 && <p role="alert" className="mb-3 text-[12.5px] text-danger">{t.of.fixStep}</p>}
        <div className="flex items-center gap-2">
          {cur > 0 && <Button type="button" variant="outline" size="lg" className="px-5" onClick={() => go(cur - 1)}><ArrowLeft className="h-4 w-4" aria-hidden />{t.of.goBack}</Button>}
          {last
            ? <Button type="submit" size="lg" className="flex-1" loading={busy} disabled={!me.user.email_verified}><Send className="h-4 w-4" aria-hidden />{t.custom.submit}</Button>
            : <Button type="submit" size="lg" className="flex-1">{t.of.goNext}<ArrowRight className="h-4 w-4" aria-hidden /></Button>}
        </div>
      </div>
    </form>
  );
}
