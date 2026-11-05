import { Globe, MapPin, MonitorSmartphone } from "lucide-react";
import type { Dict } from "@/lib/i18n";
import { cn } from "@/lib/format";
import type { Service } from "@/types/api";

const STYLE = {
  ONLINE: { Icon: Globe, cls: "bg-tint-1 text-ok" },
  REMOTE: { Icon: MonitorSmartphone, cls: "bg-tint-2 text-[#3d6496] dark:text-[#9fb8d8]" },
  LOCAL: { Icon: MapPin, cls: "bg-tint-0 text-accent" },
} as const;

/** ONLINE / REMOTE / LOCAL marker. Same shape everywhere, distinct colour and icon per type. */
export function ModeBadge({ s, t, long = false, className }: { s: Pick<Service, "mode" | "service_area">; t: Dict; long?: boolean; className?: string }) {
  const mode = (s.mode === "REMOTE" || s.mode === "LOCAL" ? s.mode : "ONLINE") as keyof typeof STYLE;
  const { Icon, cls } = STYLE[mode];
  const label = long ? t.biz.modeLong[mode].replace("{area}", s.service_area?.name ?? "") : mode === "LOCAL" && s.service_area ? `${t.biz.modes.LOCAL} · ${s.service_area.name}` : t.biz.modes[mode];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium", cls, className)}>
      <Icon className="h-3.5 w-3.5" aria-hidden />{label}
    </span>
  );
}
