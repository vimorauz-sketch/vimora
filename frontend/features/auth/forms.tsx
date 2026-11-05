"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/ui/password-input";
import { Checkbox, Field, Input } from "@/components/ui/field";
import { ErrorState, Notice } from "@/components/ui/misc";
import { api, ApiError, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { Me } from "@/types/api";

export function AuthShell({ title, sub, children }: { title: string; sub?: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[420px] px-5 py-16 sm:py-24">
      <h1 className="display text-[30px]">{title}</h1>
      {sub && <p className="mt-2 text-muted">{sub}</p>}
      <div className="mt-8">{children}</div>
    </div>
  );
}

/** Only allow same-site relative redirects after login (prevents open redirects). */
export function safeNext(v: string | null): string {
  return v && v.startsWith("/") && !v.startsWith("//") && !v.startsWith("/\\") ? v : "/dashboard";
}

export function LoginForm() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [stage, setStage] = useState<"password" | "mfa">("password");
  const [error, setError] = useState<string | null>(null);
  const schema = z.object({ email: z.string().email(), password: z.string().min(1) });
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });
  const mfa = useForm<{ code: string }>();

  async function finish() {
    const me = await api<Me>("/auth/me");
    qc.setQueryData(["me"], me);
    const next = safeNext(params.get("next"));
    router.push(me.mfa_enrollment_required ? "/dashboard/security?mfa=required" : me.user.is_staff && next === "/dashboard" ? "/admin" : next);
    router.refresh();
  }

  if (stage === "mfa") {
    return (
      <form className="space-y-5" onSubmit={mfa.handleSubmit(async ({ code }) => {
        setError(null);
        try { await api("/auth/mfa/verify", { body: { code: code.trim() } }); await finish(); } catch (e) { setError(errorMessage(e, t)); }
      })}>
        <p className="text-muted">{t.auth.mfaSub}</p>
        <Field label={t.auth.code}>{(id) => <Input id={id} autoComplete="one-time-code" inputMode="text" autoFocus maxLength={20} {...mfa.register("code", { required: true })} />}</Field>
        {error && <ErrorState message={error} />}
        <Button type="submit" className="w-full" size="lg" loading={mfa.formState.isSubmitting}>{t.auth.verify}</Button>
      </form>
    );
  }
  return (
    <form className="space-y-5" noValidate onSubmit={form.handleSubmit(async (v) => {
      setError(null);
      try {
        const r = await api<{ mfa_required: boolean }>("/auth/login", { body: { email: v.email, password: v.password } });
        if (r.mfa_required) setStage("mfa"); else await finish();
      } catch (e) {
        setError(e instanceof ApiError && e.code === "INVALID_CREDENTIALS" ? t.auth.invalid : errorMessage(e, t));
      }
    })}>
      <Field label={t.auth.email} error={form.formState.errors.email && t.errors.VALIDATION_ERROR}>{(id) => <Input id={id} type="email" autoComplete="email" {...form.register("email")} />}</Field>
      <Field label={t.auth.password}>{(id) => <PasswordInput id={id} autoComplete="current-password" {...form.register("password")} />}</Field>
      <div className="text-right text-[13.5px]"><Link href="/forgot-password" className="text-muted underline-offset-4 hover:text-fg hover:underline">{t.auth.forgot}</Link></div>
      {error && <ErrorState message={error} />}
      <Button type="submit" className="w-full" size="lg" loading={form.formState.isSubmitting}>{t.auth.signInTitle}</Button>
      <p className="text-center text-[14px] text-muted">{t.auth.noAccount} <Link href="/register" className="text-fg underline underline-offset-4">{t.nav.signUp}</Link></p>
    </form>
  );
}

/** Live checklist so the password is accepted on the first try. */
export function PasswordChecklist({ value }: { value: string }) {
  const { t } = useI18n();
  const c = t.auth.pwCheck;
  const classes = [/[a-z]/.test(value), /[A-Z]/.test(value), /\d/.test(value), /[^A-Za-z0-9]/.test(value)];
  const items: [string, boolean][] = [[c.len, value.length >= 10], [c.lower, classes[0]!], [c.upper, classes[1]!], [c.digit, classes[2]!], [c.symbol, classes[3]!]];
  const enough = classes.filter(Boolean).length >= 3;
  return (
    <ul className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[12.5px]" aria-live="polite">
      {items.map(([label, ok]) => (
        <li key={label} className={`flex items-center gap-1.5 ${ok ? "text-ok" : "text-muted"}`}>
          <span aria-hidden className={`grid h-4 w-4 place-items-center rounded-full text-[10px] ${ok ? "bg-ok text-white" : "border border-border"}`}>{ok ? "✓" : ""}</span>{label}
        </li>
      ))}
      <li className={`col-span-2 ${enough ? "text-ok" : "text-muted"}`}>{enough ? "✓ " : ""}{c.need3}</li>
    </ul>
  );
}

export function RegisterForm() {
  const { t, locale } = useI18n();
  const [done, setDone] = useState<{ email: string; delivery: string; dev?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const schema = z.object({
    full_name: z.string().trim().min(1, t.common.required).max(200),
    email: z.string().email(t.errors.VALIDATION_ERROR),
    password: z.string().max(256).refine((p) => p.length >= 10 && [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((r) => r.test(p)).length >= 3, t.auth.passwordRules),
    accept: z.literal(true, { message: t.common.required }),
  });
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });
  const e = form.formState.errors;
  if (done) return (
    <div className="space-y-4">
      <h2 className="text-[18px] font-semibold">{t.auth.registered}</h2>
      <p className="text-muted">{t.auth.registeredBody.replace("{email}", done.email)}</p>
      {done.dev && (
        <div className="space-y-3 rounded-[14px] border border-accent/40 bg-tint-0/60 p-4">
          <p className="text-[13.5px]">{t.auth.devVerify}</p>
          <Button asChild size="sm"><a href={new URL(done.dev).pathname + new URL(done.dev).search}>{t.auth.devVerifyBtn}</a></Button>
        </div>
      )}
      {done.delivery === "NOT_CONFIGURED" || done.delivery === "FAILED" ? (
        <Notice tone="warn">{t.auth.emailNotConfigured} ({t.errorInfo.label}: {done.delivery === "FAILED" ? "E1117 · EMAIL_DELIVERY_FAILED" : "E1116 · EMAIL_NOT_CONFIGURED"})</Notice>
      ) : null}
      <Button asChild variant="outline"><Link href="/login">{t.nav.signIn}</Link></Button>
    </div>
  );
  return (
    <form className="space-y-5" noValidate onSubmit={form.handleSubmit(async (v) => {
      setError(null);
      try {
        const r = await api<{ email_delivery: string; dev_verify_url?: string }>("/auth/register", { body: { email: v.email, password: v.password, full_name: v.full_name, language: locale, accept_terms: true } });
        setDone({ email: v.email, delivery: r.email_delivery, dev: r.dev_verify_url });
      } catch (err) { setError(errorMessage(err, t)); }
    })}>
      <Field label={t.auth.fullName} error={e.full_name?.message}>{(id) => <Input id={id} autoComplete="name" {...form.register("full_name")} />}</Field>
      <Field label={t.auth.email} error={e.email?.message}>{(id) => <Input id={id} type="email" autoComplete="email" {...form.register("email")} />}</Field>
      <div>
        <Field label={t.auth.password} error={e.password?.message}>{(id) => <PasswordInput id={id} autoComplete="new-password" {...form.register("password")} />}</Field>
        <PasswordChecklist value={form.watch("password") ?? ""} />
      </div>
      <div>
        <Checkbox {...form.register("accept")} label={<>{t.auth.acceptTerms} (<Link href="/terms" className="underline" target="_blank">1</Link>, <Link href="/privacy" className="underline" target="_blank">2</Link>)</>} />
        {e.accept && <p className="mt-1 text-[12.5px] text-danger">{t.common.required}</p>}
      </div>
      {error && <ErrorState message={error} />}
      <Button type="submit" className="w-full" size="lg" loading={form.formState.isSubmitting}>{t.nav.signUp}</Button>
      <p className="text-center text-[14px] text-muted">{t.auth.haveAccount} <Link href="/login" className="text-fg underline underline-offset-4">{t.nav.signIn}</Link></p>
    </form>
  );
}

export function ForgotForm() {
  const { t } = useI18n();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<{ email: string }>();
  if (sent) return <Notice tone="accent">{t.auth.linkSent}</Notice>;
  return (
    <form className="space-y-5" onSubmit={form.handleSubmit(async ({ email }) => {
      try { await api("/auth/forgot-password", { body: { email } }); setSent(true); } catch (e) { setError(errorMessage(e, t)); }
    })}>
      <Field label={t.auth.email}>{(id) => <Input id={id} type="email" autoComplete="email" required {...form.register("email", { required: true })} />}</Field>
      {error && <ErrorState message={error} />}
      <Button type="submit" className="w-full" size="lg" loading={form.formState.isSubmitting}>{t.auth.sendLink}</Button>
    </form>
  );
}

export function ResetForm() {
  const { t } = useI18n();
  const token = useSearchParams().get("token") ?? "";
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<{ password: string }>();
  if (done) return <div className="space-y-4"><Notice tone="accent">{t.auth.resetDone}</Notice><Button asChild><Link href="/login">{t.nav.signIn}</Link></Button></div>;
  return (
    <form className="space-y-5" onSubmit={form.handleSubmit(async ({ password }) => {
      setError(null);
      try { await api("/auth/reset-password", { body: { token, password } }); setDone(true); } catch (e) { setError(errorMessage(e, t)); }
    })}>
      <div>
        <Field label={t.auth.newPassword}>{(id) => <PasswordInput id={id} autoComplete="new-password" {...form.register("password", { required: true, minLength: 10 })} />}</Field>
        <PasswordChecklist value={form.watch("password") ?? ""} />
      </div>
      {error && <ErrorState message={error} />}
      <Button type="submit" className="w-full" size="lg" loading={form.formState.isSubmitting} disabled={!token}>{t.auth.setPassword}</Button>
    </form>
  );
}

export function VerifyEmail() {
  const { t } = useI18n();
  const token = useSearchParams().get("token") ?? "";
  const qc = useQueryClient();
  const [state, setState] = useState<"working" | "ok" | "fail">("working");
  const ran = useRef(false);
  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    if (!token) { setState("fail"); return; }
    api("/auth/verify-email", { body: { token } }).then(() => { setState("ok"); void qc.invalidateQueries({ queryKey: ["me"] }); }).catch(() => setState("fail"));
  }, [token, qc]);
  if (state === "working") return <p className="text-muted" role="status">{t.auth.verifying}</p>;
  if (state === "ok") return <div className="space-y-4"><Notice tone="accent">{t.auth.verified}</Notice><Button asChild><Link href="/dashboard">{t.nav.dashboard}</Link></Button></div>;
  return <ResendVerification />;
}

function ResendVerification() {
  const { t } = useI18n();
  const [sent, setSent] = useState(false);
  const [dev, setDev] = useState<string | null>(null);
  const form = useForm<{ email: string }>();
  return (
    <div className="space-y-5">
      <ErrorState message={t.auth.verifyFailed} />
      {sent ? (
        <div className="space-y-3">
          <Notice>{t.auth.linkSent}</Notice>
          {dev && <div className="space-y-3 rounded-[14px] border border-accent/40 bg-tint-0/60 p-4"><p className="text-[13.5px]">{t.auth.devVerify}</p>
            <Button asChild size="sm"><a href={new URL(dev).pathname + new URL(dev).search}>{t.auth.devVerifyBtn}</a></Button></div>}
        </div>
      ) : (
        <form className="space-y-4" onSubmit={form.handleSubmit(async ({ email }) => {
          const r = await api<{ dev_verify_url?: string }>("/auth/resend-verification", { body: { email } }).catch(() => undefined);
          setDev(r?.dev_verify_url ?? null);
          setSent(true);
        })}>
          <Field label={t.auth.email}>{(id) => <Input id={id} type="email" {...form.register("email", { required: true })} />}</Field>
          <Button type="submit" variant="outline" loading={form.formState.isSubmitting}>{t.auth.resend}</Button>
        </form>
      )}
    </div>
  );
}
