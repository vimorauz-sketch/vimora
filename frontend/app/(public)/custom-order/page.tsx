import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { CustomOrderForm } from "@/features/custom-order";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";
import type { Category } from "@/types/api";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.custom.title, description: t.custom.sub, alternates: { canonical: "/custom-order" } };
}

export default async function CustomOrderPage() {
  const { t, locale } = await getServerDict();
  const cats = await serverGet<{ items: Category[] }>(`/catalog/categories?lang=${locale}`);
  return (
    <div className="mx-auto max-w-[1160px] px-5 pb-16 pt-10 sm:px-8">
      <div className="grid gap-10 lg:grid-cols-[1fr_560px] lg:items-start">
        <aside className="lg:sticky lg:top-24">
          <p className="eyebrow">{t.co.eyebrow}</p>
          <h1 className="display mt-3 text-[38px] sm:text-[52px]">{t.custom.title}</h1>
          <p className="mt-4 max-w-[48ch] text-[16px] leading-relaxed text-muted">{t.co.lead}</p>

          <section className="mt-8">
            <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-muted">{t.co.how}</h2>
            <ol className="relative mt-4 space-y-4 before:absolute before:bottom-3 before:left-[15px] before:top-3 before:w-px before:bg-border">
              {t.co.howSteps.map((x, i) => (
                <li key={x} className="relative flex items-center gap-3.5 text-[14.5px]">
                  <span className={`relative grid h-8 w-8 shrink-0 place-items-center rounded-full text-[13px] font-semibold ${i === 0 ? "bg-accent text-accent-fg" : "border border-border bg-surface text-accent"}`}>{i + 1}</span>{x}
                </li>
              ))}
            </ol>
          </section>

          <section className="mt-8 rounded-[20px] border border-border bg-surface/70 p-5">
            <h2 className="text-[14px] font-semibold">{t.co.examplesTitle}</h2>
            <ul className="mt-3 flex flex-wrap gap-2">
              {t.co.examples.map((x) => <li key={x} className="rounded-full bg-tint-0 px-3 py-1.5 text-[13px]">{x}</li>)}
            </ul>
          </section>

          <Link href="/#composer" className="group mt-5 flex items-center gap-3 rounded-[20px] bg-ink p-5 text-ink-fg transition-transform hover:-translate-y-0.5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-ink-fg/10"><Sparkles className="h-5 w-5" aria-hidden /></span>
            <span className="flex-1"><span className="block text-[14.5px] font-semibold">{t.co.unsure}</span><span className="text-[13px] opacity-70">{t.co.askAi}</span></span>
            <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </Link>
          <p className="mt-4 text-[13px] text-muted">{t.co.free}</p>
        </aside>
        <Suspense><CustomOrderForm categories={cats?.items ?? []} /></Suspense>
      </div>
    </div>
  );
}
