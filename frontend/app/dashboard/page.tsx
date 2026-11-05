"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowRight, Check, CreditCard, Loader, Mail, MessageSquare, Package, PenLine, Sparkles, Wallet, Wrench } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { ErrorState, LoadingRows, Stat } from "@/components/ui/misc";
import { ServiceCard } from "@/features/service-card";
import { OrderRows } from "@/features/order-list";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { useArea } from "@/lib/area";
import { useI18n } from "@/lib/i18n/client";
import type { OrderSummary, Paged, Service } from "@/types/api";

type Overview = { by_status: Record<string, number>; outstanding: { currency: string; amount_minor: number }[]; action_needed: number; total: number; active: number };

export default function DashboardHome() {
  const { t, locale } = useI18n();
  const { data: me } = useMe();
  const { area } = useArea();
  const ov = useQuery({ queryKey: ["overview"], queryFn: () => api<Overview>("/orders/overview") });
  const recent = useQuery({ queryKey: ["orders", "recent"], queryFn: () => api<Paged<OrderSummary>>("/orders?page_size=5") });
  const tg = useQuery({ queryKey: ["telegram"], queryFn: () => api<{ configured: boolean; linked: boolean }>("/account/telegram") });
  const popular = useQuery({ queryKey: ["popular", locale], queryFn: () => api<Paged<Service>>(`/catalog/services?featured=true&page_size=3&lang=${locale}`), enabled: recent.data?.total === 0 });
  const [resent, setResent] = useState<string | null | false>(false);
  if (!me) return null;
  const first = me.user.full_name.split(" ")[0] || "";
  const initials = (me.user.full_name || me.user.email).split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const steps: [string, boolean, string][] = [
    [t.dx.sEmail, me.user.email_verified, "/dashboard/security"],
    [t.dx.sPhone, !!me.user.phone, "/dashboard/profile"],
    [t.dx.sArea, !!area, "/dashboard/profile"],
    ...(tg.data?.configured ? [[t.dx.sTelegram, tg.data.linked, "/dashboard/profile"] as [string, boolean, string]] : []),
    [t.dx.sOrder, (ov.data?.total ?? 0) > 0, "/services"],
  ];
  const done = steps.filter((s) => s[1]).length;
  const quick = [
    { href: "/services", icon: <Wrench />, title: t.dx.qServices, hint: t.dx.qServicesHint, tint: 0 },
    { href: "/custom-order", icon: <PenLine />, title: t.dx.qCustom, hint: t.dx.qCustomHint, tint: 4 },
    { href: "/dashboard/messages", icon: <MessageSquare />, title: t.dx.qMessages, hint: t.dx.qMessagesHint, tint: 2 },
    { href: "/dashboard/payments", icon: <CreditCard />, title: t.dx.qPayments, hint: t.dx.qPaymentsHint, tint: 1 },
  ];

  return (
    <div className="space-y-8">
      {/* welcome */}
      <section className="relative overflow-hidden rounded-[28px] border border-border bg-surface px-6 py-7 sm:px-9 sm:py-9">
        <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-[radial-gradient(closest-side,var(--glow),transparent)]" aria-hidden />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-accent text-[18px] font-semibold text-accent-fg shadow-[var(--shadow-soft)]">{initials}</span>
            <div>
              <p className="text-[12.5px] font-medium uppercase tracking-[0.14em] text-accent">{t.dx.member}</p>
              <h1 className="display text-[30px] sm:text-[38px]">{t.dash.hello.replace("{name}", first)}</h1>
              <p className="mt-1 text-[14px] text-muted">{t.dx.sub}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild size="lg"><Link href="/services">{t.dash.newOrder} <ArrowRight className="h-4 w-4" aria-hidden /></Link></Button>
            <Button asChild size="lg" variant="outline"><Link href="/custom-order">{t.nav.custom}</Link></Button>
          </div>
        </div>
      </section>

      {!me.user.email_verified && (
        <section className="flex flex-col gap-4 rounded-[22px] border border-warn/30 bg-tint-5 p-5 sm:flex-row sm:items-center">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-surface text-warn"><Mail className="h-5 w-5" aria-hidden /></span>
          <div className="flex-1 text-[14px]">
            <p className="font-semibold text-ink">{t.dx.verifyTitle}</p>
            <p className="mt-0.5 text-muted">{t.dx.verifyBody.replace("{email}", me.user.email)}</p>
          </div>
          {resent === false ? (
            <Button variant="outline" onClick={async () => { const r = await api<{ dev_verify_url?: string }>("/auth/resend-verification", { body: { email: me.user.email } }).catch(() => undefined); setResent(r?.dev_verify_url ?? null); }}>{t.of.resend}</Button>
          ) : resent ? (
            <Button asChild><a href={new URL(resent).pathname + new URL(resent).search}>{t.auth.devVerifyBtn}</a></Button>
          ) : <p className="text-[13.5px] text-ok">{t.of.resent}</p>}
        </section>
      )}

      {ov.error ? <ErrorState message={errorMessage(ov.error, t)} onRetry={() => ov.refetch()} /> : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label={t.dash.needsAction} value={ov.data?.action_needed ?? "—"} accent={!!ov.data?.action_needed} icon={<AlertCircle />} tint={5} href="/dashboard/orders" />
          <Stat label={t.dash.activeOrders} value={ov.data?.active ?? "—"} icon={<Loader />} tint={2} href="/dashboard/orders" />
          <Stat label={t.dash.totalOrders} value={ov.data?.total ?? "—"} icon={<Package />} tint={0} href="/dashboard/orders?all=1" />
          <Stat label={t.dash.outstanding} icon={<Wallet />} tint={1} href="/dashboard/payments"
            value={ov.data?.outstanding.length ? ov.data.outstanding.map((o) => <Money key={o.currency} minor={o.amount_minor} currency={o.currency} className="block text-[20px]" />) : "0"} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <section className="card p-5 sm:p-6">
            <div className="mb-4 flex items-end justify-between">
              <h2 className="text-[17px] font-semibold">{t.dash.recent}</h2>
              <Link href="/dashboard/orders" className="inline-flex items-center gap-1 text-[13.5px] text-muted hover:text-fg">{t.dash.viewAll} <ArrowRight className="h-3.5 w-3.5" aria-hidden /></Link>
            </div>
            {recent.isLoading ? <LoadingRows /> : recent.error ? <ErrorState message={errorMessage(recent.error, t)} onRetry={() => recent.refetch()} />
              : recent.data?.items.length ? <OrderRows items={recent.data.items} />
              : (
                <div className="flex flex-col items-center rounded-[18px] border border-dashed border-border px-6 py-10 text-center">
                  <span className="grid h-14 w-14 place-items-center rounded-full bg-tint-0 text-accent"><Package className="h-6 w-6" aria-hidden /></span>
                  <p className="mt-4 text-[16px] font-semibold">{t.dx.emptyTitle}</p>
                  <p className="mt-1 max-w-[42ch] text-[13.5px] text-muted">{t.dx.emptyBody}</p>
                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    <Button asChild><Link href="/services">{t.dash.browse}</Link></Button>
                    <Button asChild variant="outline"><Link href="/custom-order">{t.nav.custom}</Link></Button>
                  </div>
                </div>
              )}
          </section>
          {recent.data?.total === 0 && !!popular.data?.items.length && (
            <section>
              <h2 className="mb-4 text-[17px] font-semibold">{t.dx.popular}</h2>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">{popular.data.items.map((s) => <ServiceCard key={s.id} s={s} t={t} locale={locale} />)}</div>
            </section>
          )}
        </div>

        <aside className="space-y-6">
          <section className="card p-5">
            <h2 className="text-[15px] font-semibold">{t.dx.quick}</h2>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {quick.map((q) => (
                <Link key={q.href} href={q.href} className="group rounded-[16px] border border-border p-3.5 transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-[var(--shadow-soft)]">
                  <span className="grid h-9 w-9 place-items-center rounded-[12px] text-accent [&>svg]:h-[18px] [&>svg]:w-[18px]" style={{ background: `var(--tint-${q.tint})` }}>{q.icon}</span>
                  <span className="mt-3 block text-[13.5px] font-medium leading-tight">{q.title}</span>
                  <span className="mt-0.5 block text-[11.5px] leading-snug text-muted">{q.hint}</span>
                </Link>
              ))}
            </div>
          </section>

          {done < steps.length && (
            <section className="card p-5">
              <div className="flex items-center justify-between">
                <h2 className="text-[15px] font-semibold">{t.dx.setup}</h2>
                <span className="text-[12px] text-muted">{t.dx.stepsDone.replace("{done}", String(done)).replace("{all}", String(steps.length))}</span>
              </div>
              <p className="mt-1 text-[12.5px] text-muted">{t.dx.setupHint}</p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-raised"><div className="h-full rounded-full bg-accent transition-all" style={{ width: `${(done / steps.length) * 100}%` }} /></div>
              <ul className="mt-4 space-y-1">
                {steps.map(([label, ok, href]) => (
                  <li key={label}>
                    <Link href={href} className={`flex items-center gap-3 rounded-[12px] px-2 py-2 text-[13.5px] transition-colors hover:bg-raised ${ok ? "text-muted line-through decoration-muted/40" : ""}`}>
                      <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${ok ? "bg-ok text-white" : "border-2 border-border"}`}>{ok && <Check className="h-3 w-3" aria-hidden />}</span>
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="overflow-hidden rounded-[22px] bg-ink p-5 text-ink-fg">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-white/10"><Sparkles className="h-5 w-5" aria-hidden /></span>
            <h2 className="mt-4 text-[16px] font-semibold">{t.dx.help}</h2>
            <p className="mt-1 text-[13px] opacity-75">{t.dx.helpBody}</p>
            <Link href="/#composer" className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-[13px] font-semibold text-accent-fg transition-transform hover:-translate-y-0.5">{t.dx.helpCta} <ArrowRight className="h-3.5 w-3.5" aria-hidden /></Link>
          </section>
        </aside>
      </div>
    </div>
  );
}
