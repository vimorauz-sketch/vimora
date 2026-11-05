"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Money } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { Dialog, ErrorState, LoadingRows, PageHeader, Switch, Table } from "@/components/ui/misc";
import { TInput, emptyT } from "@/features/admin/translatable";
import { useMe } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";
import type { Translatable } from "@/types/api";

type AdminService = { id: number; slug: string; name: Translatable; category: { name: Translatable }; is_active: boolean; is_featured: boolean; ai_eligible: boolean; archived_at: string | null; order_count: number;
  pricing: { pricing_type: string; currency: string; base_price_minor: number } | null };
type Cat = { id: number; slug: string; name: Translatable; description: Translatable; icon: string; sort_order: number; is_active: boolean };

export default function AdminServices() {
  const { t, locale } = useI18n();
  const { data: me } = useMe();
  const canManage = !!me?.permissions.includes("services.manage");
  const [archived, setArchived] = useState(false);
  const q = useQuery({ queryKey: ["admin-services", archived], queryFn: () => api<{ items: AdminService[] }>(`/admin/services?include_archived=${archived}`) });
  const cats = useQuery({ queryKey: ["admin-cats"], queryFn: () => api<{ items: Cat[] }>("/admin/categories") });
  const [cat, setCat] = useState<Cat | null>(null);
  return (
    <>
      <PageHeader title={t.admin.services} actions={canManage && <><Button variant="outline" onClick={() => setCat({ id: 0, slug: "", name: emptyT(), description: emptyT(), icon: "sparkles", sort_order: 0, is_active: true })}>{t.admin.newCategory}</Button><Button asChild><Link href="/admin/services/new">{t.admin.newService}</Link></Button></>} />
      <label className="mb-4 flex items-center gap-2 text-[14px]"><input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} className="accent-[var(--accent)]" />{t.admin.archive}</label>
      {q.isLoading ? <LoadingRows /> : q.error ? <ErrorState message={errorMessage(q.error, t)} /> : (
        <Table head={[t.admin.name, t.admin.category, t.admin.pricingType, t.services.price, t.common.status, t.admin.orders]}>
          {q.data?.items.map((s) => (
            <tr key={s.id} className="hover:bg-surface">
              <td className="px-4 py-3"><Link href={`/admin/services/${s.id}`} className="font-medium hover:underline">{s.name[locale] || s.name.en || s.slug}</Link><span className="block text-[12px] text-muted">{s.slug}</span></td>
              <td className="px-4 py-3">{s.category.name[locale] || s.category.name.en}</td>
              <td className="px-4 py-3 text-[13px]">{s.pricing?.pricing_type}</td>
              <td className="px-4 py-3">{s.pricing && s.pricing.pricing_type !== "CUSTOM_QUOTE" ? <Money minor={s.pricing.base_price_minor} currency={s.pricing.currency} /> : "—"}</td>
              <td className="px-4 py-3 text-[13px]">{s.archived_at ? "archived" : s.is_active ? <span className="text-ok">{t.admin.active}</span> : <span className="text-muted">off</span>}{s.is_featured && " · ★"}{s.ai_eligible && " · AI"}</td>
              <td className="px-4 py-3 tabular-nums">{s.order_count}</td>
            </tr>
          ))}
        </Table>
      )}
      <h2 className="mb-3 mt-10 text-[17px] font-semibold">{t.admin.categories}</h2>
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {cats.data?.items.map((c) => (
          <li key={c.id}><button disabled={!canManage} onClick={() => setCat(c)} className="flex w-full justify-between rounded-[8px] border border-border px-4 py-3 text-left text-[14px] hover:border-fg/40">
            <span>{c.name[locale] || c.name.en}</span><span className={c.is_active ? "text-muted" : "text-danger"}>{c.is_active ? c.slug : "off"}</span>
          </button></li>
        ))}
      </ul>
      {cat && <CategoryDialog cat={cat} onClose={() => { setCat(null); void cats.refetch(); }} />}
    </>
  );
}

function CategoryDialog({ cat, onClose }: { cat: Cat; onClose: () => void }) {
  const { t } = useI18n();
  const [c, setC] = useState(cat);
  async function save() {
    try {
      const body = { slug: c.slug, name: c.name, description: c.description, icon: c.icon, sort_order: c.sort_order, is_active: c.is_active };
      await api(c.id ? `/admin/categories/${c.id}` : "/admin/categories", { method: c.id ? "PUT" : "POST", body });
      onClose();
    } catch (e) { toast.error(errorMessage(e, t)); }
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} title={c.id ? t.common.edit : t.admin.newCategory} footer={<Button onClick={save}>{t.common.save}</Button>}>
      <div className="space-y-4">
        <Field label={t.admin.slug}>{(id) => <Input id={id} value={c.slug} onChange={(e) => setC({ ...c, slug: e.target.value.toLowerCase() })} pattern="[a-z0-9-]+" />}</Field>
        <TInput label={t.admin.name} value={c.name} onChange={(v) => setC({ ...c, name: v })} required />
        <TInput label={t.admin.fullDesc} value={c.description} onChange={(v) => setC({ ...c, description: v })} />
        <div className="grid grid-cols-2 gap-3">
          <Field label={t.admin.icon}>{(id) => <Input id={id} value={c.icon} onChange={(e) => setC({ ...c, icon: e.target.value })} />}</Field>
          <Field label="#">{(id) => <Input id={id} type="number" value={c.sort_order} onChange={(e) => setC({ ...c, sort_order: Number(e.target.value) })} />}</Field>
        </div>
        <Switch label={t.admin.active} checked={c.is_active} onCheckedChange={(v) => setC({ ...c, is_active: v })} />
      </div>
    </Dialog>
  );
}
