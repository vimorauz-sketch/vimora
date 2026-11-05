import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/logo";
import { getServerDict } from "@/lib/i18n/server";

export default async function NotFound() {
  const { t } = await getServerDict();
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-[720px] flex-col justify-center px-6">
      <Logo />
      <p className="display mt-16 text-[96px] text-muted/40">404</p>
      <h1 className="display mt-2 text-[32px]">{t.pages.notFound}</h1>
      <p className="mt-3 text-muted">{t.pages.notFoundBody}</p>
      <div className="mt-8 flex gap-3"><Button asChild><Link href="/">{t.pages.home}</Link></Button><Button asChild variant="outline"><Link href="/services">{t.nav.services}</Link></Button></div>
    </main>
  );
}
