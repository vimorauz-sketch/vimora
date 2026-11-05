"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell, CreditCard, FolderDown, LayoutGrid, MessageSquare, Package, ShieldCheck, User } from "lucide-react";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useMe } from "@/hooks/queries";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { data: me } = useMe();
  const unread = useQuery({ queryKey: ["notif-count"], queryFn: () => api<{ unread: number }>("/account/notifications?unread=true"), enabled: !!me && !me.mfa_pending, refetchInterval: 60_000 });
  const nav = [
    { href: "/dashboard", label: t.dash.overview, icon: <LayoutGrid />, exact: true, group: t.dx.groupWork },
    { href: "/dashboard/orders", label: t.dash.orders, icon: <Package />, group: t.dx.groupWork },
    { href: "/dashboard/messages", label: t.dash.messages, icon: <MessageSquare />, group: t.dx.groupWork },
    { href: "/dashboard/payments", label: t.dash.payments, icon: <CreditCard />, group: t.dx.groupWork },
    { href: "/dashboard/deliverables", label: t.dash.deliverables, icon: <FolderDown />, group: t.dx.groupWork },
    { href: "/dashboard/notifications", label: t.dash.notifications, icon: <Bell />, badge: unread.data?.unread, group: t.dx.groupAccount },
    { href: "/dashboard/profile", label: t.dash.profile, icon: <User />, group: t.dx.groupAccount },
    { href: "/dashboard/security", label: t.dash.security, icon: <ShieldCheck />, group: t.dx.groupAccount },
  ];
  return <AppShell nav={nav} home="/dashboard">{children}</AppShell>;
}
