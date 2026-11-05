import type { Metadata } from "next";
import { FaqList } from "@/features/home/faq";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.pages.faq, alternates: { canonical: "/faq" } };
}

export default async function FaqPage() {
  const { t, locale } = await getServerDict();
  const faq = await serverGet<{ items: { id: number; question: string; answer: string }[] }>(`/faq?lang=${locale}`);
  return (
    <div className="mx-auto max-w-[860px] px-5 py-14 sm:px-8">
      <h1 className="display mb-10 text-[32px] sm:text-[44px]">{t.pages.faq}</h1>
      {faq && faq.items.length ? <FaqList items={faq.items} /> : <p className="text-muted">{t.common.empty}</p>}
    </div>
  );
}
