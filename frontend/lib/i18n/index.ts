import en, { type Dict } from "./en";
import ru from "./ru";
import uz from "./uz";

export const LOCALES = ["uz", "en", "ru"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "uz";
export const LOCALE_COOKIE = "vimora_lang";
export const LOCALE_LABELS: Record<Locale, string> = { uz: "O'zbekcha", en: "English", ru: "Русский" };

const dicts: Record<Locale, Dict> = { uz, en, ru };

export function isLocale(v: unknown): v is Locale {
  return typeof v === "string" && (LOCALES as readonly string[]).includes(v);
}

export function getDict(locale: Locale): Dict {
  return dicts[locale];
}

/** Replace {name} placeholders. */
export function fmt(template: string, vars: Record<string, string | number> = {}): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => (k in vars ? String(vars[k]) : `{${k}}`));
}

export type { Dict };
