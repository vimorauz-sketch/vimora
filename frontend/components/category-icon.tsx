import {
  BrainCircuit, Clapperboard, CodeXml, Database, FileText, Globe, GraduationCap, Image as ImageIcon, Landmark, Megaphone, Languages,
  MonitorCog, PenTool, Plug, Printer, Send, Server, Sheet, Sparkles, type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/format";

const ICONS: Record<string, LucideIcon> = {
  "monitor-cog": MonitorCog, "file-text": FileText, sheet: Sheet, languages: Languages, "pen-tool": PenTool, image: ImageIcon,
  clapperboard: Clapperboard, instagram: Megaphone, megaphone: Megaphone, globe: Globe, send: Send, "code-xml": CodeXml, database: Database, server: Server,
  plug: Plug, "brain-circuit": BrainCircuit, landmark: Landmark, "graduation-cap": GraduationCap, sparkles: Sparkles, printer: Printer,
};

/** Soft tinted icon chips; each category gets its own warm tint so the catalog scans quickly. */
const TINTS = [0, 1, 2, 3, 4, 5].map((i) => `var(--tint-${i})`);

export function CategoryIcon({ name, index = 0, size = "md" }: { name: string; index?: number; size?: "xs" | "sm" | "md" | "lg" }) {
  const Icon = ICONS[name] ?? Sparkles;
  const box = size === "lg" ? "h-14 w-14" : size === "sm" ? "h-9 w-9" : size === "xs" ? "h-7 w-7" : "h-11 w-11";
  const ico = size === "lg" ? "h-6 w-6" : size === "sm" ? "h-4 w-4" : size === "xs" ? "h-3.5 w-3.5" : "h-5 w-5";
  return (
    <span className={cn("grid shrink-0 place-items-center text-accent", size === "xs" ? "rounded-full" : "rounded-2xl", box)} style={{ background: TINTS[index % TINTS.length] }} aria-hidden>
      <Icon className={ico} strokeWidth={1.75} />
    </span>
  );
}
