import { BadgeCheck, Check, CreditCard, Globe2, Layers, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";
import { CategoryIcon } from "@/components/category-icon";
import { CheckItem } from "@/components/domain";
import { Button } from "@/components/ui/button";
import { Composer } from "@/features/home/composer";
import { FaqList } from "@/features/home/faq";
import { HeroVisual } from "@/features/home/hero-visual";
import { TypewriterHeadline } from "@/features/home/typewriter";
import { ServiceCard } from "@/features/service-card";
import { fmt } from "@/lib/i18n";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";
import type { Category, Paged, Service } from "@/types/api";

type Stats = { completed_orders: number; active_services: number; categories: number; average_rating: number | null; public_reviews: number };
type Testimonial = { rating: number; text: string; author: string; service: string | null; date: string };

const WHY_ICONS = [Layers, CreditCard, ShieldCheck, Globe2];

export default async function Home() {
  const { t, locale } = await getServerDict();
  const [featured, cats, stats, testimonials, faq] = await Promise.all([
    serverGet<Paged<Service>>(`/catalog/services?lang=${locale}&featured=true&page_size=6`),
    serverGet<{ items: Category[] }>(`/catalog/categories?lang=${locale}`),
    serverGet<Stats>("/stats"),
    serverGet<{ items: Testimonial[] }>(`/testimonials?lang=${locale}`),
    serverGet<{ items: { id: number; question: string; answer: string }[] }>(`/faq?lang=${locale}`),
  ]);
  let popular = featured?.items ?? [];
  if (popular.length < 3) popular = (await serverGet<Paged<Service>>(`/catalog/services?lang=${locale}&page_size=6`))?.items ?? popular;
  const categories = (cats?.items ?? []).filter((c) => (c.service_count ?? 0) > 0);
  const statItems = stats
    ? ([
        stats.completed_orders > 0 && { v: stats.completed_orders, l: t.home.statsCompleted },
        stats.active_services > 0 && { v: stats.active_services, l: t.home.statsServices },
        stats.categories > 0 && { v: stats.categories, l: t.home.statsCategories },
        stats.average_rating !== null && { v: stats.average_rating.toFixed(1), l: t.home.statsRating },
      ].filter(Boolean) as { v: string | number; l: string }[])
    : [];
  const trustIcons = [Zap, ShieldCheck, BadgeCheck];

  return (
    <>
      {/* HERO */}
      <section className="warm-glow">
        <div className="mx-auto grid max-w-[1240px] items-center gap-14 px-5 pb-20 pt-14 sm:px-8 sm:pt-20 lg:grid-cols-[1.25fr_1fr]">
          <div>
            <p className="eyebrow">{t.home.eyebrow}</p>
            <TypewriterHeadline a={t.home.h1a} em={t.home.h1em} b={t.home.h1b} className="display mt-6 text-[clamp(2.6rem,5.6vw,4.9rem)] text-ink" />
            <p className="mt-7 max-w-[54ch] text-[17px] leading-relaxed text-muted">{t.home.sub2}</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Button asChild size="lg"><Link href="/services">{t.home.chooseService} <span aria-hidden>→</span></Link></Button>
              <Button asChild size="lg" variant="outline"><Link href="/custom-order">{t.home.customOrder}</Link></Button>
            </div>
            <ul className="mt-9 flex flex-wrap gap-x-6 gap-y-2 text-[14px] text-muted">
              {t.home.trust.map((x, i) => {
                const Icon = trustIcons[i] ?? Check;
                return <li key={x} className="flex items-center gap-2"><Icon className="h-4 w-4 text-accent" strokeWidth={1.75} aria-hidden />{x}</li>;
              })}
            </ul>
          </div>
          <HeroVisual t={t} />
        </div>
      </section>

      {/* CATEGORIES */}
      {categories.length > 0 && (
        <section className="mx-auto max-w-[1240px] px-5 pt-20 sm:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="display text-[34px] text-ink sm:text-[42px]">{t.home.categories}</h2>
              <p className="mt-3 max-w-[60ch] text-muted">{t.home.categoriesSub}</p>
            </div>
            <Button asChild variant="outline"><Link href="/services">{t.home.catalogCta}</Link></Button>
          </div>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {categories.map((c, i) => (
              <li key={c.id}>
                <Link href={`/services?category=${c.slug}`} className="card card-hover flex h-full items-center gap-4 p-4">
                  <CategoryIcon name={c.icon} index={i} />
                  <span className="min-w-0">
                    <span className="block font-medium leading-snug text-ink">{c.name}</span>
                    <span className="mt-0.5 block text-[13px] text-muted">{fmt(t.home.servicesCount, { n: c.service_count ?? 0 })}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* POPULAR */}
      {popular.length > 0 && (
        <section className="mx-auto max-w-[1240px] px-5 pt-24 sm:px-8">
          <div className="flex items-end justify-between gap-4">
            <h2 className="display text-[34px] text-ink sm:text-[42px]">{t.home.popular}</h2>
            <Link href="/services" className="text-[14.5px] font-medium text-accent underline-offset-4 hover:underline">{t.home.allServices} →</Link>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {popular.slice(0, 6).map((s, i) => <ServiceCard key={s.id} s={s} t={t} locale={locale} index={i} />)}
          </div>
        </section>
      )}

      {/* HOW IT WORKS */}
      <section id="how" className="mt-24 scroll-mt-24 bg-raised/60 py-20">
        <div className="mx-auto max-w-[1240px] px-5 sm:px-8">
          <h2 className="display text-[34px] text-ink sm:text-[42px]">{t.home.processTitle}</h2>
          <ol className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {t.home.steps.map((s, i) => (
              <li key={s.t} className="card p-6">
                <span className="grid h-10 w-10 place-items-center rounded-full bg-accent font-[family-name:var(--font-display)] text-[17px] text-accent-fg">{i + 1}</span>
                <h3 className="mt-5 font-[family-name:var(--font-display)] text-[21px] text-ink">{s.t}</h3>
                <p className="mt-2 text-[14.5px] leading-relaxed text-muted">{s.d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* AI + HUMAN */}
      <section className="mx-auto max-w-[1240px] px-5 pt-24 sm:px-8">
        <div className="grid gap-10 rounded-[28px] border border-border bg-soft p-8 sm:p-14 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <h2 className="display text-[32px] text-ink sm:text-[40px]">{t.home.verifyTitle}</h2>
            <p className="mt-5 max-w-[58ch] leading-relaxed text-fg/75">{t.home.verifyBody}</p>
          </div>
          <ul className="space-y-4 self-center text-[15.5px] text-ink">{t.home.verifyPoints.map((p) => <CheckItem key={p}>{p}</CheckItem>)}</ul>
        </div>
      </section>

      {/* ASSISTANT */}
      <section id="composer" className="mx-auto max-w-[1240px] scroll-mt-24 px-5 pt-24 sm:px-8">
        <div className="grid items-center gap-10 lg:grid-cols-[1fr_1.2fr]">
          <div>
            <h2 className="display text-[32px] text-ink sm:text-[40px]">{t.home.composerTitle}</h2>
            <p className="mt-4 max-w-[48ch] text-muted">{t.home.composerSub}</p>
          </div>
          <Composer />
        </div>
      </section>

      {/* WHY */}
      <section className="mx-auto max-w-[1240px] px-5 pt-24 sm:px-8">
        <h2 className="display text-[34px] text-ink sm:text-[42px]">{t.home.whyTitle}</h2>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {t.home.why.map((w, i) => {
            const Icon = WHY_ICONS[i] ?? Check;
            return (
              <div key={w.t} className="card p-6">
                <Icon className="h-6 w-6 text-accent" strokeWidth={1.6} aria-hidden />
                <h3 className="mt-4 font-[family-name:var(--font-display)] text-[19px] text-ink">{w.t}</h3>
                <p className="mt-2 text-[14.5px] leading-relaxed text-muted">{w.d}</p>
              </div>
            );
          })}
        </div>
      </section>

      {statItems.length > 0 && (
        <section className="mx-auto max-w-[1240px] px-5 pt-20 sm:px-8" aria-label={t.home.statsTitle}>
          <dl className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {statItems.map((s) => (
              <div key={s.l} className="card px-6 py-5">
                <dt className="sr-only">{s.l}</dt>
                <dd className="display text-[46px] tabular-nums text-ink">{s.v}</dd>
                <dd className="text-[14px] text-muted">{s.l}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {testimonials && testimonials.items.length > 0 && (
        <section className="mx-auto max-w-[1240px] px-5 pt-24 sm:px-8">
          <h2 className="display text-[34px] text-ink sm:text-[42px]">{t.home.testimonials}</h2>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {testimonials.items.map((r, i) => (
              <figure key={i} className="card p-6">
                <p className="text-[15px] text-accent" aria-label={`${r.rating}/5`}>{"★".repeat(r.rating)}<span className="text-border">{"★".repeat(5 - r.rating)}</span></p>
                <blockquote className="mt-3 font-[family-name:var(--font-display)] text-[17px] leading-relaxed text-ink">“{r.text}”</blockquote>
                <figcaption className="mt-4 text-[13px] text-muted">{r.author}{r.service ? `, ${r.service}` : ""}</figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      {faq && faq.items.length > 0 && (
        <section className="mx-auto grid max-w-[1240px] gap-10 px-5 pt-24 sm:px-8 lg:grid-cols-[1fr_2fr]">
          <h2 className="display text-[34px] text-ink sm:text-[42px]">{t.home.faqTitle}</h2>
          <FaqList items={faq.items.slice(0, 6)} />
        </section>
      )}

      <section className="mx-auto max-w-[1240px] px-5 pt-24 sm:px-8">
        <div className="warm-glow flex flex-col items-start justify-between gap-8 rounded-[28px] border border-border bg-surface p-10 shadow-[var(--shadow-soft)] md:flex-row md:items-center sm:p-14">
          <div>
            <h2 className="display text-[34px] text-ink sm:text-[44px]">{t.home.ctaTitle}</h2>
            <p className="mt-3 text-muted">{t.home.ctaBody}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg"><Link href="/services">{t.home.chooseService} <span aria-hidden>→</span></Link></Button>
            <Button asChild size="lg" variant="outline"><Link href="/assistant">{t.nav.assistant}</Link></Button>
          </div>
        </div>
      </section>
    </>
  );
}
