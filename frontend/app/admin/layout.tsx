"use client";

import { BarChart3, Bot, Coins, Cog, FileText, Gauge, Map as MapIcon, MapPin, Package, ScrollText, Tag, Users, Wallet, Wrench } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AdminNotifier } from "@/features/admin/notifier";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/misc";
import { useMe } from "@/hooks/queries";
import { useI18n } from "@/lib/i18n/client";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { data: me } = useMe();
  const can = (p: string) => !!me?.permissions.includes(p);
  const nav = [
    { href: "/admin", label: t.admin.overview, icon: <Gauge />, exact: true, show: true },
    { href: "/admin/orders", label: t.admin.orders, icon: <Package />, show: can("orders.view") },
    { href: "/admin/local-orders", label: t.admin.localOrders, icon: <MapPin />, show: can("orders.view") },
    { href: "/admin/ai", label: t.admin.ai, icon: <Bot />, show: can("ai.view") },
    { href: "/admin/services", label: t.admin.services, icon: <Wrench />, show: can("orders.view") },
    { href: "/admin/pricing", label: t.admin.prices, icon: <Coins />, show: can("orders.view") },
    { href: "/admin/areas", label: t.admin.areas, icon: <MapIcon />, show: can("orders.view") },
    { href: "/admin/customers", label: t.admin.customers, icon: <Users />, show: can("customers.view") },
    { href: "/admin/finance", label: t.admin.finance, icon: <Wallet />, show: can("finance.view") },
    { href: "/admin/analytics", label: t.admin.analytics, icon: <BarChart3 />, show: can("analytics.view") },
    { href: "/admin/promo-codes", label: t.admin.promos, icon: <Tag />, show: can("services.manage") },
    { href: "/admin/content", label: t.admin.content, icon: <FileText />, show: can("settings.manage") || can("orders.view") },
    { href: "/admin/settings", label: t.admin.settings, icon: <Cog />, show: can("settings.manage") },
    { href: "/admin/audit", label: t.admin.audit, icon: <ScrollText />, show: can("audit.view") },
  ].filter((n) => n.show);
  return (
    <AppShell nav={nav} home="/admin" requireStaff>
      {me?.mfa_enrollment_required ? (
        <div className="max-w-xl space-y-4">
          <Notice tone="warn">{t.admin.mfaSetup}</Notice>
          <Button asChild><Link href="/dashboard/security?mfa=required">{t.admin.goSecurity}</Link></Button>
        </div>
      ) : children}
      {!me?.mfa_enrollment_required && <AdminNotifier />}
    </AppShell>
  );
}
