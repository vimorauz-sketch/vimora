"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Confirm, ErrorState, LoadingRows, PageHeader, Panel } from "@/components/ui/misc";
import { OrderRows } from "@/features/order-list";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import type { OrderSummary, Payment } from "@/types/api";

type Detail = { id: number; email: string; full_name: string; is_active: boolean; email_verified: boolean; roles: string[]; created_at: string; last_login_at: string | null; phone: string | null; company: string | null; language: string; mfa_enabled: boolean;
  orders: OrderSummary[]; payments?: Payment[]; activity: { action: string; ip: string | null; success: boolean; created_at: string }[] };

export default function CustomerDetail() {
  const { t, locale } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { data: me } = useMe();
  const can = (p: string) => !!me?.permissions.includes(p);
  const q = useQuery({ queryKey: ["customer", id], queryFn: () => api<Detail>(`/admin/customers/${id}`) });
  if (q.isLoading) return <LoadingRows />;
  if (q.error || !q.data) return <ErrorState message={errorMessage(q.error, t)} />;
  const c = q.data;
  const run = async (path: string, body: unknown = {}) => { try { await api(path, { body }); void q.refetch(); toast.success(t.common.saved); } catch (e) { toast.error(errorMessage(e, t)); } };
  return (
    <>
      <PageHeader title={c.full_name || c.email} sub={`${c.email} · ${c.roles.join(", ")}`} actions={can("customers.manage") && (c.is_active
        ? <Confirm danger title={t.admin.disable} body={c.email} confirmLabel={t.admin.disable} onConfirm={() => run(`/admin/customers/${c.id}/disable`)} trigger={<Button variant="danger">{t.admin.disable}</Button>} />
        : <Button variant="outline" onClick={() => run(`/admin/customers/${c.id}/restore`)}>{t.admin.enable}</Button>)} />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <section><h2 className="mb-3 text-[16px] font-semibold">{t.admin.orders}</h2>{c.orders.length ? <OrderRows items={c.orders} base="/admin/orders" staff /> : <p className="text-muted">{t.common.empty}</p>}</section>
          {c.payments && (
            <Panel title={t.dash.payments}>
              {c.payments.length ? <ul className="divide-y divide-border text-[14px]">{c.payments.map((p) => <li key={p.id} className="flex justify-between py-2"><span>{p.provider} · {p.reference} · {date(p.created_at, locale)}</span><span><Money minor={p.amount_minor} currency={p.currency} /> {p.status}</span></li>)}</ul> : <p className="text-muted">{t.common.empty}</p>}
            </Panel>
          )}
        </div>
        <aside className="space-y-6">
          <Panel title={t.dash.profile}>
            <dl className="space-y-2 text-[14px]">
              {([[t.dash.phone, c.phone], [t.dash.company, c.company], [t.dash.language, c.language], [t.dash.mfa, c.mfa_enabled ? t.dash.mfaOn : t.dash.mfaOff], [t.dash.created, date(c.created_at, locale)], [t.admin.lastLogin, date(c.last_login_at, locale, true)]] as [string, string | null][]).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3"><dt className="text-muted">{k}</dt><dd>{v || "—"}</dd></div>
              ))}
            </dl>
            <p className="mt-3 text-[12px] text-muted">{t.admin.secretsNote}</p>
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-border pt-4 text-[14px]">
              <span className={c.email_verified ? "text-ok" : "text-warn"}>{c.email_verified ? `✓ ${t.admin.emailVerified}` : t.admin.unverified}</span>
              {!c.email_verified && can("customers.manage") && <Button size="sm" variant="outline" onClick={() => run(`/admin/customers/${c.id}/verify-email`)}>{t.admin.verifyEmail}</Button>}
            </div>
          </Panel>
          {can("staff.manage") && (
            <Panel title={t.admin.staffRole}>
              <div className="flex flex-wrap gap-2">
                {(["SUPPORT", "ADMIN", "SUPER_ADMIN"] as const).map((r) => {
                  const has = c.roles.includes(r);
                  return <Confirm key={r} danger={has} title={`${has ? t.admin.revokeRole : t.admin.grant} ${r}`} confirmLabel={t.common.confirm} onConfirm={() => run(`/admin/customers/${c.id}/roles`, { role: r, grant: !has })}
                    trigger={<Button size="sm" variant={has ? "secondary" : "outline"}>{has ? "✓ " : ""}{r}</Button>} />;
                })}
              </div>
            </Panel>
          )}
          <Panel title={t.admin.activity}>
            <ul className="space-y-1.5 text-[13px]">{c.activity.map((a, i) => <li key={i} className="flex justify-between gap-2"><span className={a.success ? "" : "text-danger"}>{a.action}</span><span className="text-muted">{date(a.created_at, locale, true)}</span></li>)}</ul>
          </Panel>
        </aside>
      </div>
    </>
  );
}
