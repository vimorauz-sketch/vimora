"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/ui/password-input";
import { Field, Input } from "@/components/ui/field";
import { Dialog, Notice, PageHeader, Panel } from "@/components/ui/misc";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { PasswordChecklist } from "@/features/auth/forms";
import { useI18n } from "@/lib/i18n/client";

type Sess = { id: number; current: boolean; ip_address: string | null; user_agent: string | null; created_at: string; last_seen_at: string };

export default function SecurityPage() {
  return <Suspense><Security /></Suspense>;
}

function Security() {
  const { t, locale } = useI18n();
  const router = useRouter();
  const required = useSearchParams().get("mfa") === "required";
  const qc = useQueryClient();
  const { data: me } = useMe();
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: () => api<{ items: Sess[] }>("/account/sessions") });
  const pw = useForm<{ current_password: string; new_password: string }>();
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [disableOpen, setDisableOpen] = useState<null | "mfa" | "deactivate">(null);
  const [password, setPassword] = useState("");
  if (!me) return null;
  return (
    <>
      <PageHeader title={t.dash.security} />
      {(required || me.mfa_enrollment_required) && <div className="mb-6"><Notice tone="warn">{t.auth.mfaEnrollRequired}</Notice></div>}
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title={t.dash.mfa} actions={<span className={me.user.mfa_enabled ? "text-ok" : "text-muted"}>{me.user.mfa_enabled ? t.dash.mfaOn : t.dash.mfaOff}</span>}>
          {codes ? (
            <div className="space-y-3">
              <p className="font-medium">{t.dash.recoveryCodes}</p>
              <p className="text-[13.5px] text-muted">{t.dash.recoveryHint}</p>
              <ul className="grid grid-cols-2 gap-2 font-mono text-[14px]">{codes.map((c) => <li key={c} className="rounded border border-border px-2 py-1">{c}</li>)}</ul>
              <Button variant="outline" size="sm" onClick={() => { void navigator.clipboard.writeText(codes.join("\n")); toast.success(t.common.copied); }}>{t.common.copy}</Button>
              {me.user.is_staff && <Button size="sm" className="ml-2" onClick={() => router.push("/admin")}>{t.nav.admin}</Button>}
            </div>
          ) : me.user.mfa_enabled ? (
            <Button variant="danger" onClick={() => setDisableOpen("mfa")}>{t.dash.mfaDisable}</Button>
          ) : setup ? (
            <div className="space-y-4">
              <p className="text-[14px] text-muted">{t.dash.mfaScan}</p>
              <div className="inline-block rounded-[8px] bg-white p-3"><QRCodeSVG value={setup.otpauth_uri} size={168} /></div>
              <p className="text-[13px] text-muted">{t.dash.mfaSecret}: <code className="select-all break-all text-fg">{setup.secret}</code></p>
              <div className="flex gap-2">
                <Input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" maxLength={6} placeholder="123456" aria-label={t.auth.code} className="max-w-[160px]" />
                <Button onClick={async () => {
                  try { const r = await api<{ recovery_codes: string[] }>("/account/mfa/enable", { body: { code } }); setCodes(r.recovery_codes); void qc.invalidateQueries({ queryKey: ["me"] }); }
                  catch (e) { toast.error(errorMessage(e, t)); }
                }}>{t.auth.verify}</Button>
              </div>
            </div>
          ) : (
            <Button onClick={async () => { try { setSetup(await api("/account/mfa/setup", { method: "POST" })); } catch (e) { toast.error(errorMessage(e, t)); } }}>{t.dash.mfaEnable}</Button>
          )}
        </Panel>
        <Panel title={t.dash.changePassword}>
          <form className="space-y-4" onSubmit={pw.handleSubmit(async (v) => {
            try { await api("/account/change-password", { body: v }); pw.reset(); toast.success(t.dash.passwordChanged); void sessions.refetch(); } catch (e) { toast.error(errorMessage(e, t)); }
          })}>
            <Field label={t.dash.currentPassword}>{(id) => <PasswordInput id={id} autoComplete="current-password" {...pw.register("current_password", { required: true })} />}</Field>
            <div>
              <Field label={t.auth.newPassword}>{(id) => <PasswordInput id={id} autoComplete="new-password" {...pw.register("new_password", { required: true, minLength: 10 })} />}</Field>
              <PasswordChecklist value={pw.watch("new_password") ?? ""} />
            </div>
            <Button type="submit" loading={pw.formState.isSubmitting}>{t.dash.changePassword}</Button>
          </form>
        </Panel>
        <Panel title={t.dash.sessions} className="lg:col-span-2" actions={<Button variant="ghost" size="sm" onClick={async () => { await api("/account/sessions/revoke-others", { method: "POST" }); void sessions.refetch(); }}>{t.dash.revokeOthers}</Button>}>
          <ul className="divide-y divide-border text-[14px]">
            {sessions.data?.items.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate">{s.user_agent ?? "—"}</p>
                  <p className="text-[12.5px] text-muted">{s.ip_address} · {date(s.last_seen_at, locale, true)}</p>
                </div>
                {s.current ? <span className="text-[13px] text-accent">{t.dash.current}</span> : <Button variant="ghost" size="sm" onClick={async () => { await api(`/account/sessions/${s.id}`, { method: "DELETE" }); void sessions.refetch(); }}>{t.dash.revoke}</Button>}
              </li>
            ))}
          </ul>
        </Panel>
        {!me.user.roles.includes("SUPER_ADMIN") && (
          <Panel title={t.dash.deactivate} className="lg:col-span-2">
            <p className="mb-4 text-[14px] text-muted">{t.dash.deactivateHint}</p>
            <Button variant="danger" onClick={() => setDisableOpen("deactivate")}>{t.dash.deactivate}</Button>
          </Panel>
        )}
      </div>
      <Dialog open={!!disableOpen} onOpenChange={(o) => !o && setDisableOpen(null)} title={disableOpen === "mfa" ? t.dash.mfaDisable : t.dash.deactivate}
        footer={<Button variant="danger" onClick={async () => {
          try {
            await api(disableOpen === "mfa" ? "/account/mfa/disable" : "/account/deactivate", { body: { password } });
            setDisableOpen(null); setPassword("");
            if (disableOpen === "deactivate") { qc.clear(); router.push("/"); } else void qc.invalidateQueries({ queryKey: ["me"] });
          } catch (e) { toast.error(errorMessage(e, t)); }
        }}>{t.common.confirm}</Button>}>
        <Field label={t.dash.passwordToConfirm}>{(id) => <PasswordInput id={id} value={password} onChange={(e) => setPassword(e.target.value)} />}</Field>
      </Dialog>
    </>
  );
}
