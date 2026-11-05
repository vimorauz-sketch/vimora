import type { MetadataRoute } from "next";
import { serverGet } from "@/lib/server-api";
import type { Paged, Service } from "@/types/api";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
  const statics = ["", "/services", "/assistant", "/custom-order", "/about", "/faq", "/contact", "/terms", "/privacy", "/refund-policy", "/service-policy", "/ai-notice"];
  const out: MetadataRoute.Sitemap = statics.map((p) => ({ url: `${base}${p}`, changeFrequency: "weekly", priority: p === "" ? 1 : 0.6 }));
  for (let page = 1; page <= 20; page++) {
    const data = await serverGet<Paged<Service>>(`/catalog/services?page=${page}&page_size=60`, { revalidate: 3600 });
    if (!data || data.items.length === 0) break;
    out.push(...data.items.map((s) => ({ url: `${base}/services/${s.slug}`, changeFrequency: "weekly" as const, priority: 0.8 })));
    if (page * 60 >= data.total) break;
  }
  return out;
}
