import type { Metadata } from "next";
import { ContactForm } from "@/features/contact";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.pages.contact, alternates: { canonical: "/contact" } };
}

export default async function ContactPage() {
  const { t } = await getServerDict();
  const site = await serverGet<Record<string, string>>("/site", { revalidate: 120 });
  const email = site?.["platform.contact_email"];
  const tg = site?.["platform.contact_telegram"];
  return (
    <div className="mx-auto grid max-w-[1100px] gap-12 px-5 py-14 sm:px-8 lg:grid-cols-[1fr_1.3fr]">
      <div>
        <h1 className="display text-[32px] sm:text-[44px]">{t.pages.contact}</h1>
        <p className="mt-3 text-muted">{t.pages.contactSub}</p>
        <dl className="mt-8 space-y-3 text-[15px]">
          {email && <div><dt className="text-[13px] text-muted">Email</dt><dd><a className="underline underline-offset-4" href={`mailto:${email}`}>{email}</a></dd></div>}
          {tg && <div><dt className="text-[13px] text-muted">Telegram</dt><dd><a className="underline underline-offset-4" href={`https://t.me/${tg.replace(/^@/, "")}`} rel="noopener noreferrer" target="_blank">{tg}</a></dd></div>}
        </dl>
      </div>
      <ContactForm />
    </div>
  );
}
