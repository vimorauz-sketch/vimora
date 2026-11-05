"use client";

import { useState } from "react";
import { Input, Textarea } from "@/components/ui/field";
import { LOCALES } from "@/lib/i18n";
import { cn } from "@/lib/format";
import type { Translatable } from "@/types/api";

export const emptyT = (): Translatable => ({ uz: "", en: "", ru: "" });

/** Edits one translatable value with uz/en/ru tabs. */
export function TInput({ label, value, onChange, multiline, required }: { label: string; value: Translatable; onChange: (v: Translatable) => void; multiline?: boolean; required?: boolean }) {
  const [lang, setLang] = useState<(typeof LOCALES)[number]>("uz");
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-medium">{label}{required && " *"}</span>
        <div className="flex gap-0.5 text-[12px]" role="group" aria-label={`${label} language`}>
          {LOCALES.map((l) => (
            <button key={l} type="button" onClick={() => setLang(l)} aria-pressed={lang === l}
              className={cn("rounded px-1.5 py-0.5 uppercase", lang === l ? "bg-raised" : "text-muted", !value[l] && "italic")}>{l}</button>
          ))}
        </div>
      </div>
      {multiline
        ? <Textarea aria-label={`${label} (${lang})`} value={value[lang] ?? ""} onChange={(e) => onChange({ ...value, [lang]: e.target.value })} rows={5} />
        : <Input aria-label={`${label} (${lang})`} value={value[lang] ?? ""} onChange={(e) => onChange({ ...value, [lang]: e.target.value })} />}
    </div>
  );
}
