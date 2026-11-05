"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useMe } from "@/hooks/queries";
import { api } from "@/lib/api";
import { cn } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import { Logo } from "./logo";
import { LangSwitch, ThemeToggle } from "./switchers";

export function Header() {
  const { t } = useI18n();
  const path = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const [open, setOpen] = useState(false);
  const links = [
    { href: "/", label: t.nav.home },
    { href: "/services", label: t.nav.services },
    { href: "/#how", label: t.nav.how },
    { href: "/custom-order", label: t.nav.custom },
    { href: "/faq", label: t.nav.faq },
    { href: "/contact", label: t.nav.contact },
  ];
  async function signOut() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    qc.setQueryData(["me"], null);
    router.push("/");
    router.refresh();
  }
  const isActive = (href: string) => (href === "/" ? path === "/" : !href.includes("#") && path.startsWith(href));
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex h-[72px] max-w-[1240px] items-center gap-6 px-5 sm:px-8">
        <Logo />
        <nav className="ml-auto hidden items-center gap-0.5 xl:flex" aria-label="Main">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className={cn("whitespace-nowrap rounded-full px-3 py-2 text-[14.5px] transition-colors", isActive(l.href) ? "text-ink font-medium" : "text-fg/80 hover:text-ink")}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto hidden items-center gap-2 xl:ml-2 xl:flex">
          <LangSwitch />
          <ThemeToggle />
          {me ? (
            <>
              <Button asChild variant="dark" size="md"><Link href="/dashboard">{t.nav.dashboard}</Link></Button>
              <Button variant="ghost" size="sm" onClick={signOut}>{t.nav.signOut}</Button>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm"><Link href="/login">{t.nav.signIn}</Link></Button>
              <Button asChild variant="dark" size="md"><Link href="/services">{t.nav.order}</Link></Button>
            </>
          )}
        </div>
        <button className="ml-auto rounded-full p-2 xl:hidden" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="mobile-nav" aria-label={t.nav.menu}>
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <div id="mobile-nav" className="border-t border-border bg-bg px-5 pb-6 xl:hidden">
          <nav className="flex flex-col py-2" aria-label="Main">
            {links.map((l) => <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="border-b border-border py-3.5 text-[15.5px]">{l.label}</Link>)}
          </nav>
          <div className="flex items-center gap-3 pt-4"><LangSwitch /><ThemeToggle /></div>
          <div className="mt-4 flex gap-2">
            {me ? (
              <><Button asChild variant="dark" className="flex-1"><Link href="/dashboard" onClick={() => setOpen(false)}>{t.nav.dashboard}</Link></Button><Button variant="outline" onClick={signOut}>{t.nav.signOut}</Button></>
            ) : (
              <><Button asChild variant="outline" className="flex-1"><Link href="/login">{t.nav.signIn}</Link></Button><Button asChild variant="dark" className="flex-1"><Link href="/services">{t.nav.order}</Link></Button></>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
