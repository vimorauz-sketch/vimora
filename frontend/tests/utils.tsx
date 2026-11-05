import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";
import { I18nProvider } from "@/lib/i18n/client";
import type { Locale } from "@/lib/i18n";

export const router = { push: vi.fn(), replace: vi.fn(), refresh: vi.fn(), back: vi.fn() };
export let pathname = "/";
export const setPath = (p: string) => { pathname = p; };
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => pathname,
  useSearchParams: () => new URLSearchParams(globalThis.__search ?? ""),
  useParams: () => ({}),
}));

declare global { var __search: string | undefined }

export function renderWith(ui: ReactElement, locale: Locale = "en") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><I18nProvider locale={locale}>{ui}</I18nProvider></QueryClientProvider>);
}

export function mockFetch(handler: (url: string, init?: RequestInit) => { status?: number; body?: unknown }) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const r = handler(url, init);
    return new Response(r.body === undefined ? null : JSON.stringify(r.body), { status: r.status ?? 200, headers: { "content-type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
