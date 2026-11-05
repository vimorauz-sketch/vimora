import Link from "next/link";
import { ModeBadge } from "@/components/mode-badge";
import { ServicePhoto } from "@/components/service-photo";
import { money } from "@/lib/format";
import type { Dict, Locale } from "@/lib/i18n";
import type { Service } from "@/types/api";

export function priceLabel(s: Service, t: Dict, locale: Locale): string {
  const p = s.pricing;
  if (!p || p.pricing_type === "CUSTOM_QUOTE") return t.services.customQuote;
  const amount = money(p.base_price_minor, p.currency, locale);
  if (p.pricing_type === "FIXED") return amount;
  const unit = p.unit_label ? ` / ${p.unit_label}` : "";
  return p.pricing_type === "STARTING_FROM" ? `${locale === "en" ? "from " : ""}${amount}${unit}${locale === "en" ? "" : ` ${t.services.startingFrom}`}` : `${amount}${unit}`;
}

export function ServiceCard({ s, t, locale, index = 0 }: { s: Service; t: Dict; locale: Locale; index?: number }) {
  const custom = !s.pricing || s.pricing.pricing_type === "CUSTOM_QUOTE";
  return (
    <Link href={`/services/${s.slug}`} className="card card-hover group flex flex-col gap-5 p-4">
      <div className="relative overflow-hidden rounded-[12px]">
        <ModeBadge s={s} t={t} className="absolute left-2.5 top-2.5 z-10 shadow-sm" />
        <ServicePhoto src={s.image_url} slug={s.slug} category={s.category.slug} alt={s.name}
          className="aspect-[16/10] w-full transition-transform duration-500 group-hover:scale-[1.03]" />
      </div>
      <div className="flex-1 px-1">
        <p className="text-[12.5px] text-muted">{s.category.name}</p>
        <h3 className="mt-1 font-[family-name:var(--font-display)] text-[19px] font-medium leading-snug text-ink">{s.name}</h3>
        {s.short_description && <p className="mt-2 line-clamp-2 text-[14px] leading-relaxed text-muted">{s.short_description}</p>}
      </div>
      <div className="flex items-center justify-between gap-3 mx-1 border-t border-border pt-4 text-[13.5px]">
        <span className={custom ? "text-muted" : "font-semibold tabular-nums text-ink"}>{priceLabel(s, t, locale)}</span>
        <span className="text-accent transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden>→</span>
      </div>
    </Link>
  );
}
