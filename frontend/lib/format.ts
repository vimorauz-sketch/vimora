import type { Locale } from "./i18n";

const intlLocale: Record<Locale, string> = { uz: "uz-UZ", en: "en-US", ru: "ru-RU" };

const UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];

/** Thousands grouping with a narrow no-break space (consistent across browsers; uz ICU data is often missing). */
function group(n: number, fraction: boolean): string {
  const [whole, frac] = Math.abs(n).toFixed(fraction ? 2 : 0).split(".");
  const g = whole!.replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f");
  return `${n < 0 ? "−" : ""}${g}${frac ? `,${frac}` : ""}`;
}

/** Money is always integer minor units from the API; formatting never does arithmetic beyond /100. */
export function money(minor: number | null | undefined, currency: string, locale: Locale = "uz"): string {
  if (minor === null || minor === undefined) return "—";
  const major = minor / 100;
  const whole = Number.isInteger(major);
  if (currency === "UZS") {
    const n = locale === "en" ? new Intl.NumberFormat("en-US", { minimumFractionDigits: whole ? 0 : 2 }).format(major) : group(major, !whole);
    return `${n} ${locale === "ru" ? "сум" : locale === "uz" ? "so'm" : "UZS"}`;
  }
  return new Intl.NumberFormat(intlLocale[locale], { style: "currency", currency, minimumFractionDigits: 2 }).format(major);
}

/** Parse a user-entered major amount ("150 000", "19.99") into integer minor units without float drift. */
export function toMinor(input: string): number | null {
  const clean = input.replace(/[\s,]/g, (c) => (c === "," ? "." : ""));
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  const [whole, frac = ""] = clean.split(".");
  return Number(whole) * 100 + Number(frac.padEnd(2, "0"));
}

export function fromMinor(minor: number): string {
  const s = String(Math.abs(minor)).padStart(3, "0");
  const out = `${s.slice(0, -2)}.${s.slice(-2)}`.replace(/\.00$/, "");
  return minor < 0 ? `-${out}` : out;
}

export function date(iso: string | null | undefined, locale: Locale = "uz", withTime = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (locale === "uz") {
    // Browsers ship incomplete Uzbek date data ("2026 M11 2"), so format explicitly.
    const base = `${d.getDate()}-${UZ_MONTHS[d.getMonth()]}, ${d.getFullYear()}`;
    return withTime ? `${base}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}` : base;
  }
  return new Intl.DateTimeFormat(intlLocale[locale], withTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(d);
}

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
