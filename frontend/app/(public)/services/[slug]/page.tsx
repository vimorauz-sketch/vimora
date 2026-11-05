import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { BackLink } from "@/components/back-link";
import { ModeBadge } from "@/components/mode-badge";
import { ServicePhoto } from "@/components/service-photo";
import { notFound } from "next/navigation";
import { OrderForm } from "@/features/order-form";
import { priceLabel } from "@/features/service-card";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";
import type { Service } from "@/types/api";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const { locale } = await getServerDict();
  const s = await serverGet<Service>(`/catalog/services/${encodeURIComponent(slug)}?lang=${locale}`);
  if (!s) return {};
  return { title: s.name, description: s.short_description || s.description?.slice(0, 160), alternates: { canonical: `/services/${s.slug}` }, openGraph: { title: s.name, description: s.short_description } };
}

export default async function ServicePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { t, locale } = await getServerDict();
  const s = await serverGet<Service>(`/catalog/services/${encodeURIComponent(slug)}?lang=${locale}`, { revalidate: 30 });
  if (!s) notFound();
  const jsonLd = { "@context": "https://schema.org", "@type": "Service", name: s.name, description: s.short_description, provider: { "@type": "Organization", name: "VIMORA" } };
  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-14 pt-8 sm:px-8">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />
      <nav aria-label={t.services.title} className="mb-8 flex flex-wrap items-center gap-x-4 gap-y-3">
        <BackLink fallback={`/services?category=${s.category.slug}`} label={t.common.back} />
        <ol className="flex flex-wrap items-center gap-1.5 text-[13px] text-muted">
          <li><Link href="/services" className="hover:text-fg hover:underline">{t.services.title}</Link></li>
          <li aria-hidden><ChevronRight className="h-3.5 w-3.5" /></li>
          <li><Link href={`/services?category=${s.category.slug}`} className="hover:text-fg hover:underline">{s.category.name}</Link></li>
          <li aria-hidden><ChevronRight className="h-3.5 w-3.5" /></li>
          <li aria-current="page" className="max-w-[40ch] truncate text-fg">{s.name}</li>
        </ol>
      </nav>
      <div className="flex flex-wrap items-center gap-3"><ModeBadge s={s} t={t} /><p className="text-[13px] text-muted">{s.category.name}</p></div>
      <h1 className="display mt-3 text-[32px] sm:text-[46px]">{s.name}</h1>
      {s.short_description && <p className="mt-3 max-w-[64ch] text-[16px] text-muted">{s.short_description}</p>}
      <div className="mt-12 grid gap-12 lg:grid-cols-[1fr_440px]">
        <div className="space-y-10">
          <figure>
            <ServicePhoto src={s.image_url} slug={s.slug} category={s.category.slug} alt={s.name} eager className="aspect-[16/9] w-full rounded-[18px]" />
            {s.image_url && s.image_credit && <figcaption className="mt-2 text-[12px] text-muted">{t.services.photoBy} {s.image_credit}</figcaption>}
          </figure>
          {s.description && s.description !== s.short_description && <div className="prose-vimora whitespace-pre-line text-[16px]">{s.description}</div>}
          <section className="rounded-[18px] border border-border bg-raised/40 p-5">
            <h2 className="text-[15px] font-semibold">{t.biz.method}</h2>
            <p className="mt-1.5 text-[14.5px] leading-relaxed text-fg/85">{t.biz.modeHow[s.mode === "REMOTE" || s.mode === "LOCAL" ? s.mode : "ONLINE"].replace("{area}", s.service_area?.name ?? "")}</p>
          </section>
          <dl className="grid grid-cols-2 gap-6 border-y border-border py-6 text-[14px] sm:grid-cols-4">
            <div><dt className="text-muted">{t.biz.availability}</dt><dd className="mt-1 font-medium">{s.mode === "LOCAL" ? s.service_area?.name : t.biz.everywhere}</dd></div>
            <div><dt className="text-muted">{t.services.price}</dt><dd className="mt-1 font-medium tabular-nums">{priceLabel(s, t, locale)}</dd></div>
            {s.estimated_delivery && <div><dt className="text-muted">{t.biz.duration}</dt><dd className="mt-1 font-medium">{s.estimated_delivery}</dd></div>}
            {s.ai_eligible && <div><dt className="text-muted">{t.services.aiAssisted}</dt><dd className="mt-1">{t.home.verifyPoints[0]}</dd></div>}
          </dl>
          {s.required_fields && s.required_fields.length > 0 && (
            <section>
              <h2 className="text-[17px] font-semibold">{t.services.requirements}</h2>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-muted">{s.required_fields.map((f) => <li key={f.key}>{f.label}</li>)}</ul>
            </section>
          )}
          {s.examples && s.examples.length > 0 && (
            <section>
              <h2 className="text-[17px] font-semibold">{t.services.examples}</h2>
              <div className="mt-4 space-y-4">{s.examples.map((e, i) => <div key={i} className="border-l-2 border-accent pl-4"><p className="font-medium">{e.title}</p><p className="mt-1 text-muted">{e.text}</p></div>)}</div>
            </section>
          )}
        </div>
        <aside className="lg:sticky lg:top-24 lg:self-start">
          {s.is_active ? <OrderForm service={s} /> : <p className="rounded-[10px] border border-border p-6 text-muted">{t.services.unavailable}</p>}
        </aside>
      </div>
    </div>
  );
}
