"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Menu, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useMe } from "@/hooks/queries";
import { api } from "@/lib/api";
import { cn } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import { LoadingRows } from "@/components/ui/misc";
import { Logo } from "./logo";
import { LangSwitch, ThemeToggle } from "./switchers";

export type NavItem = { href: string; label: string; icon: ReactNode; exact?: boolean; badge?: number; group?: string };

/** Authenticated application shell shared by the customer dashboard and the admin panel. */
export function AppShell({ nav, children, requireStaff, home }: { nav: NavItem[]; children: ReactNode; requireStaff?: boolean; home: string }) {
  const { t } = useI18n();
  const { data: me, isLoading } = useMe();
  const router = useRouter();
  const path = usePathname();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (isLoading) return;
    if (!me) router.replace(`/login?next=${encodeURIComponent(path)}`);
    else if (me.mfa_pending) router.replace(`/login?next=${encodeURIComponent(path)}`);
    else if (requireStaff && !me.user.is_staff) router.replace("/dashboard");
  }, [me, isLoading, requireStaff, router, path]);
  useEffect(() => setOpen(false), [path]);
  if (isLoading || !me || me.mfa_pending || (requireStaff && !me.user.is_staff)) return <div className="mx-auto max-w-3xl p-10"><LoadingRows /></div>;
  async function signOut() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    qc.clear();
    router.push("/");
  }
  const initials = (me.user.full_name || me.user.email).split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const sidebar = (
    <nav aria-label="Sections" className="flex flex-col gap-0.5">
      {nav.map((n, i) => {
        const active = n.exact ? path === n.href : path === n.href || path.startsWith(`${n.href}/`);
        const heading = n.group && n.group !== nav[i - 1]?.group ? n.group : null;
        return (
          <div key={n.href}>
            {heading && <p className={cn("px-3.5 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted/80", i > 0 && "mt-5")}>{heading}</p>}
            <Link href={n.href} aria-current={active ? "page" : undefined}
              className={cn("group relative flex items-center gap-3 rounded-[14px] px-3.5 py-2.5 text-[14px] transition-all",
                active ? "bg-surface font-medium text-fg shadow-[var(--shadow-soft)]" : "text-muted hover:bg-surface/70 hover:text-fg")}>
              {active && <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-accent" aria-hidden />}
              <span className={cn("grid h-8 w-8 place-items-center rounded-[10px] transition-colors [&>svg]:h-[17px] [&>svg]:w-[17px]", active ? "bg-tint-0 text-accent" : "group-hover:text-accent")}>{n.icon}</span>
              <span className="flex-1">{n.label}</span>
              {!!n.badge && <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] font-semibold text-accent-fg tabular-nums">{n.badge}</span>}
            </Link>
          </div>
        );
      })}
    </nav>
  );
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="hidden border-r border-border bg-raised/50 lg:flex lg:flex-col">
        <div className="flex h-16 items-center px-5"><Logo href={home} /></div>
        <div className="flex-1 px-3 py-4">{sidebar}</div>
        <div className="space-y-3 border-t border-border p-4">
          <Link href={home === "/admin" ? "/dashboard/profile" : "/dashboard/profile"} className="flex items-center gap-3 rounded-[14px] bg-surface p-2.5 shadow-[var(--shadow-soft)] transition-colors hover:bg-surface/80">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent text-[13px] font-semibold text-accent-fg">{initials}</span>
            <span className="min-w-0">
              <span className="block truncate text-[13.5px] font-medium text-fg">{me.user.full_name || "—"}</span>
              <span className="block truncate text-[12px] text-muted" title={me.user.email}>{me.user.email}</span>
            </span>
          </Link>
          <div className="flex items-center gap-2"><LangSwitch /><ThemeToggle /></div>
          <div className="flex gap-3 text-[13px]">
            {home === "/admin" && <Link href="/dashboard" className="text-muted hover:text-fg">{t.nav.dashboard}</Link>}
            <Link href="/" className="text-muted hover:text-fg">VIMORA</Link>
            <button onClick={signOut} className="ml-auto text-muted hover:text-fg">{t.nav.signOut}</button>
          </div>
        </div>
      </aside>
      <div className="flex h-14 items-center justify-between border-b border-border px-4 lg:hidden">
        <Logo href={home} />
        <button onClick={() => setOpen(!open)} aria-expanded={open} aria-label={t.nav.menu} className="p-2">{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
      </div>
      {open && (
        <div className="space-y-4 border-b border-border p-4 lg:hidden">
          {sidebar}
          <div className="flex items-center justify-between"><div className="flex items-center gap-2"><LangSwitch /><ThemeToggle /></div><button onClick={signOut} className="text-[14px] text-muted">{t.nav.signOut}</button></div>
        </div>
      )}
      <main id="main" className="min-w-0 px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
        <div className="mx-auto max-w-[1160px]">{children}</div>
      </main>
    </div>
  );
}
