"use client";

import { Building2, Globe2, Home, Map, MapPin } from "lucide-react";
import { useRouter } from "next/navigation";
import { PrettySelect } from "@/components/ui/pretty-select";
import { useArea, useAreas } from "@/lib/area";
import { useI18n } from "@/lib/i18n/client";
import type { Area } from "@/types/api";

const ICON: Record<Area["kind"], React.ReactNode> = { LOCALITY: <Home />, DISTRICT: <Map />, REGION: <Building2 />, OTHER: <Globe2 /> };

/** Manual area choice (no GPS). Saved in a cookie; server pages re-render with it. */
export function AreaPicker({ className, onChange, size = "md", id }: { className?: string; compact?: boolean; onChange?: (slug: string | null) => void; size?: "md" | "lg"; id?: string }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const { area, setArea } = useArea();
  const areas = useAreas(locale);
  const options = (areas.data?.items ?? []).map((a) => ({
    value: a.slug, label: a.name, icon: ICON[a.kind],
    hint: [a.district, a.region].filter(Boolean).join(" · ") || t.biz.everywhere,
    badge: a.local_services_enabled ? t.biz.modes.LOCAL : undefined,
  }));
  return (
    <PrettySelect id={id} className={className} size={size} value={area} placeholder={t.biz.chooseArea} aria-label={t.biz.chooseArea} icon={<MapPin />}
      options={options} onValueChange={(v) => { setArea(v); onChange?.(v); router.refresh(); }} />
  );
}
