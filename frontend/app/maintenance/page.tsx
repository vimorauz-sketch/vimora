import { Logo } from "@/components/layout/logo";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export default async function Maintenance() {
  const { t, locale } = await getServerDict();
  const site = await serverGet<Record<string, unknown>>("/site", { revalidate: false });
  const msg = (site?.["platform.maintenance_message"] as Record<string, string> | undefined)?.[locale];
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-[720px] flex-col justify-center px-6">
      <Logo />
      <h1 className="display mt-16 text-[36px]">{t.pages.maintenance}</h1>
      <p className="mt-4 text-muted">{msg || t.pages.maintenanceBody}</p>
      <div className="mt-10 h-[3px] w-40 overflow-hidden rounded-full bg-border"><div className="h-full w-1/3 animate-pulse bg-accent" /></div>
    </main>
  );
}
