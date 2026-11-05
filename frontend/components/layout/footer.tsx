import Link from "next/link";
import { getServerDict } from "@/lib/i18n/server";
import { Logo } from "./logo";

export async function Footer() {
  const { t } = await getServerDict();
  const cols = [
    { title: t.nav.services, links: [{ href: "/services", l: t.nav.services }, { href: "/assistant", l: t.nav.assistant }, { href: "/custom-order", l: t.nav.custom }] },
    { title: t.footer.company, links: [{ href: "/about", l: t.nav.about }, { href: "/faq", l: t.nav.faq }, { href: "/contact", l: t.nav.contact }] },
    { title: t.footer.legal, links: [{ href: "/terms", l: t.pages.terms }, { href: "/privacy", l: t.pages.privacy }, { href: "/refund-policy", l: t.pages.refund }, { href: "/service-policy", l: t.pages.servicePolicy }, { href: "/ai-notice", l: t.pages.aiNotice }] },
  ];
  return (
    <footer className="mt-28 border-t border-border bg-raised/50">
      <div className="mx-auto grid max-w-[1240px] gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <Logo />
          <p className="mt-4 max-w-[30ch] text-[14px] text-muted">{t.footer.tagline}</p>
        </div>
        {cols.map((c) => (
          <div key={c.title}>
            <h2 className="text-[13px] font-medium text-muted">{c.title}</h2>
            <ul className="mt-4 space-y-2.5 text-[14px]">
              {c.links.map((l) => <li key={l.href}><Link href={l.href} className="hover:underline underline-offset-4">{l.l}</Link></li>)}
            </ul>
          </div>
        ))}
      </div>
      <div className="mx-auto max-w-[1240px] border-t border-border px-5 py-5 text-[12.5px] text-muted sm:px-8">© {new Date().getFullYear()} VIMORA. {t.footer.rights}</div>
    </footer>
  );
}
