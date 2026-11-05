"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Toaster } from "sonner";
import { NavTracker } from "@/components/back-link";
import { ApiError } from "@/lib/api";
import { I18nProvider } from "@/lib/i18n/client";
import type { Locale } from "@/lib/i18n";

export function Providers({ locale, children }: { locale: Locale; children: ReactNode }) {
  const [client] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: { retry: (n, e) => !(e instanceof ApiError && e.status < 500) && n < 2, refetchOnWindowFocus: false },
        mutations: { retry: false },
      },
    }),
  );
  return (
    <QueryClientProvider client={client}>
      <I18nProvider locale={locale}>
        {children}
        <NavTracker />
        <Toaster position="bottom-right" toastOptions={{ style: { background: "var(--raised)", color: "var(--fg)", border: "1px solid var(--border)", borderRadius: 8 } }} />
      </I18nProvider>
    </QueryClientProvider>
  );
}
