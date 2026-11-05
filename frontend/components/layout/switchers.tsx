"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { LOCALES, LOCALE_LABELS } from "@/lib/i18n";
import { useI18n } from "@/lib/i18n/client";

export function LangSwitch() {
  const { locale, setLocale, t } = useI18n();
  return (
    <div role="group" aria-label={t.nav.language} className="flex items-center rounded-full border border-border bg-surface p-0.5 text-[12px] font-medium">
      {LOCALES.map((l) => (
        <button key={l} type="button" onClick={() => setLocale(l)} aria-pressed={l === locale} title={LOCALE_LABELS[l]}
          className={`rounded-full px-2.5 py-1 uppercase transition-colors ${l === locale ? "bg-ink text-ink-fg" : "text-muted hover:text-fg"}`}>
          {l}
        </button>
      ))}
    </div>
  );
}

/** Light / dark switch. Stored in a cookie so the server renders the right theme (no flash). */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const { t } = useI18n();
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  }, []);
  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    document.cookie = `vimora_theme=${next}; path=/; max-age=31536000; samesite=lax`;
    setTheme(next);
  }
  const label = theme === "dark" ? t.nav.light : t.nav.dark;
  return (
    <button type="button" onClick={toggle} aria-label={`${t.nav.theme}: ${label}`} title={label}
      className={`grid h-9 w-9 shrink-0 place-items-center rounded-full border border-border bg-surface text-fg transition-colors hover:border-accent/60 hover:text-accent ${className}`}>
      {theme === "dark" ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
    </button>
  );
}
