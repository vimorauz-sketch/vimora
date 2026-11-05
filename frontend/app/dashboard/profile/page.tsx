"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, BadgeCheck, BellRing, Clock3, Globe2, Languages, Mail, Send, UserRound } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { PrettySelect } from "@/components/ui/pretty-select";
import { AreaPicker } from "@/features/local/area-picker";
import { date } from "@/lib/format";
import { Confirm, Notice, Switch } from "@/components/ui/misc";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { LOCALES, LOCALE_LABELS, type Locale } from "@/lib/i18n";
import { useI18n } from "@/lib/i18n/client";

type ProfileF = { full_name: string; phone: string; company: string; language: Locale; timezone: string };
const OPTIONAL = ["order.status", "message.received", "final_payment.reminder"] as const;

export default function ProfilePage() {
  const { t, locale, setLocale } = useI18n();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const form = useForm<ProfileF>();
  useEffect(() => { if (me) form.reset({ full_name: me.user.full_name, phone: me.user.phone ?? "", company: me.user.company ?? "", language: me.user.language, timezone: me.user.timezone }); }, [me, form]);
  const [prefs, setPrefs] = useState<Record<string, Record<string, boolean>>>({});
  useEffect(() => { if (me) setPrefs(me.user.notification_prefs ?? {}); }, [me]);
  const tg = useQuery({ queryKey: ["telegram"], queryFn: () => api<{ configured: boolean; linked: boolean; username: string | null; notifications_enabled: boolean }>("/account/telegram") });
  const [deepLink, setDeepLink] = useState<string | null>(null);
  if (!me) return null;
  const pref = (ch: string, k: string) => prefs[ch]?.[k] ?? true;
  async function savePrefs(next: typeof prefs) {
    setPrefs(next);
    try { await api("/account/notification-preferences", { method: "PUT", body: { email: next.email ?? {}, telegram: next.telegram ?? {} } }); void qc.invalidateQueries({ queryKey: ["me"] }); }
    catch (e) { toast.error(errorMessage(e, t)); }
  }
  const initials = (me.user.full_name || me.user.email).split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const tzOptions = ["Asia/Tashkent", "Asia/Samarkand", "Europe/Moscow", "Europe/Istanbul", "Asia/Dubai", "UTC"].map((z) => ({ value: z, label: z.replace("_", " ") }));
  return (
    <div className="space-y-6">
      {/* header */}
      <section className="relative overflow-hidden rounded-[28px] border border-border bg-surface px-6 py-7 sm:px-9">
        <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-[radial-gradient(closest-side,var(--glow),transparent)]" aria-hidden />
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center">
          <span className="grid h-20 w-20 shrink-0 place-items-center rounded-full bg-accent text-[26px] font-semibold text-accent-fg shadow-[var(--shadow-lift)] ring-4 ring-surface">{initials}</span>
          <div className="min-w-0 flex-1">
            <h1 className="display truncate text-[30px] sm:text-[36px]">{me.user.full_name || me.user.email}</h1>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13.5px] text-muted">
              <span className="inline-flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" aria-hidden />{me.user.email}</span>
              <span>{t.pf.since.replace("{date}", date(me.user.created_at, locale))}</span>
            </p>
          </div>
          <span className={`inline-flex items-center gap-1.5 self-start rounded-full px-3 py-1.5 text-[12.5px] font-medium sm:self-center ${me.user.email_verified ? "bg-tint-1 text-ok" : "bg-tint-5 text-warn"}`}>
            {me.user.email_verified ? <BadgeCheck className="h-4 w-4" aria-hidden /> : <AlertCircle className="h-4 w-4" aria-hidden />}
            {me.user.email_verified ? t.pf.verified : t.pf.notVerified}
          </span>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
        <form className="card overflow-hidden" onSubmit={form.handleSubmit(async (v) => {
          try {
            await api("/account/profile", { method: "PATCH", body: { ...v, phone: v.phone || null, company: v.company || null } });
            toast.success(t.dash.profileSaved);
            void qc.invalidateQueries({ queryKey: ["me"] });
            setLocale(v.language);
          } catch (e) { toast.error(errorMessage(e, t)); }
        })}>
          <SectionHead icon={<UserRound />} title={t.pf.personal} hint={t.pf.personalHint} />
          <div className="grid gap-4 px-6 pb-6 sm:grid-cols-2">
            <div className="sm:col-span-2"><Field label={t.auth.fullName}>{(id) => <Input id={id} className="h-11 rounded-[14px]" {...form.register("full_name", { required: true })} />}</Field></div>
            <Field label={t.dash.phone}>{(id) => <Input id={id} type="tel" className="h-11 rounded-[14px]" placeholder={t.pf.phonePh} {...form.register("phone")} />}</Field>
            <Field label={t.dash.company} optional={t.common.optional}>{(id) => <Input id={id} className="h-11 rounded-[14px]" placeholder={t.pf.companyPh} {...form.register("company")} />}</Field>
          </div>
          <div className="border-t border-border" />
          <SectionHead icon={<Globe2 />} title={t.pf.region} hint={t.pf.regionHint} />
          <div className="grid gap-4 px-6 pb-6 sm:grid-cols-2">
            <Field label={t.dash.language}>{(id) => (
              <PrettySelect id={id} aria-label={t.dash.language} value={form.watch("language")} onValueChange={(v) => form.setValue("language", v as Locale, { shouldDirty: true })}
                options={LOCALES.map((l) => ({ value: l, label: LOCALE_LABELS[l], icon: <Languages /> }))} />
            )}</Field>
            <Field label={t.dash.timezone}>{(id) => (
              <PrettySelect id={id} aria-label={t.dash.timezone} value={form.watch("timezone")} onValueChange={(v) => form.setValue("timezone", v, { shouldDirty: true })}
                options={tzOptions.some((o) => o.value === form.watch("timezone")) ? tzOptions : [...tzOptions, { value: form.watch("timezone"), label: form.watch("timezone") }]} icon={<Clock3 />} />
            )}</Field>
            <div className="sm:col-span-2"><p className="mb-1.5 text-[13px] font-medium">{t.biz.yourArea}</p><AreaPicker /></div>
          </div>
          <div className="flex justify-end border-t border-border bg-raised/40 px-6 py-4">
            <Button type="submit" loading={form.formState.isSubmitting}>{t.pf.save}</Button>
          </div>
        </form>

        <div className="space-y-6">
          <section className="card overflow-hidden">
            <SectionHead icon={<BellRing />} title={t.dash.notifPrefs} hint={t.dash.notifPrefsHint} />
            <div className="px-6 pb-6">
              <div className="grid grid-cols-[1fr_auto_auto] items-center gap-x-6 gap-y-3 text-[13.5px]">
                <span className="text-[12px] font-semibold uppercase tracking-wide text-muted">{t.pf.channel}</span>
                <span className="text-center text-[12px] font-semibold text-muted">{t.dash.emailNotif}</span>
                <span className="text-center text-[12px] font-semibold text-muted">{t.dash.telegramNotif}</span>
                {OPTIONAL.map((k) => (
                  <Fragment key={k}>
                    <span>{t.dash.ev[k]}</span>
                    {(["email", "telegram"] as const).map((ch) => (
                      <span key={ch} className="flex justify-center">
                        <Switch label={<span className="sr-only">{`${t.dash.ev[k]} · ${ch}`}</span>} checked={pref(ch, k)} onCheckedChange={(v) => savePrefs({ ...prefs, [ch]: { ...(prefs[ch] ?? {}), [k]: v } })} />
                      </span>
                    ))}
                  </Fragment>
                ))}
              </div>
            </div>
          </section>
          <section className="card overflow-hidden">
            <SectionHead icon={<Send />} title={t.dash.telegram} />
            <div className="px-6 pb-6">
              {!tg.data?.configured ? <p className="rounded-[14px] bg-raised/60 px-4 py-3 text-[13.5px] text-muted">{t.dash.telegramNotConfigured}</p> : tg.data.linked ? (
                <div className="space-y-3">
                  <p className="text-[14px]">{t.dash.telegramLinked.replace("{user}", tg.data.username ?? "—")}</p>
                  <Switch label={t.dash.telegramNotif} checked={tg.data.notifications_enabled} onCheckedChange={async (v) => { await api(`/account/telegram/toggle?enabled=${v}`, { method: "POST" }); void tg.refetch(); }} />
                  <Confirm title={t.dash.telegramUnlink} confirmLabel={t.dash.telegramUnlink} onConfirm={async () => { await api("/account/telegram", { method: "DELETE" }); void tg.refetch(); }}
                    trigger={<Button variant="ghost" size="sm">{t.dash.telegramUnlink}</Button>} />
                </div>
              ) : (
                <div className="space-y-3">
                  <Button variant="outline" onClick={async () => { try { setDeepLink((await api<{ deep_link: string }>("/account/telegram/link", { method: "POST" })).deep_link); } catch (e) { toast.error(errorMessage(e, t)); } }}>{t.dash.telegramLink}</Button>
                  {deepLink && <Notice><p>{t.dash.telegramOpen}</p><a href={deepLink} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block underline">{deepLink}</a></Notice>}
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function SectionHead({ icon, title, hint }: { icon: React.ReactNode; title: string; hint?: string }) {
  return (
    <div className="flex items-start gap-3 px-6 pb-5 pt-6">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[12px] bg-tint-0 text-accent [&>svg]:h-5 [&>svg]:w-5">{icon}</span>
      <div><h2 className="text-[16px] font-semibold">{title}</h2>{hint && <p className="mt-0.5 text-[13px] text-muted">{hint}</p>}</div>
    </div>
  );
}
