import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import localFont from "next/font/local";
import { cookies } from "next/headers";
import type { ReactNode } from "react";
import { Providers } from "@/components/providers";
import { getServerDict } from "@/lib/i18n/server";
import "@/styles/globals.css";

const serif = localFont({
  src: [
    { path: "./fonts/lora-latin-wght-normal.woff2", weight: "400 700", style: "normal" },
    { path: "./fonts/lora-latin-ext-wght-normal.woff2", weight: "400 700", style: "normal" },
    { path: "./fonts/lora-cyrillic-wght-normal.woff2", weight: "400 700", style: "normal" },
    { path: "./fonts/lora-latin-wght-italic.woff2", weight: "400 700", style: "italic" },
    { path: "./fonts/lora-latin-ext-wght-italic.woff2", weight: "400 700", style: "italic" },
    { path: "./fonts/lora-cyrillic-wght-italic.woff2", weight: "400 700", style: "italic" },
  ],
  variable: "--font-serif",
  display: "swap",
});

const SITE = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return {
    metadataBase: new URL(SITE),
    title: { default: t.meta.title, template: "%s — VIMORA" },
    description: t.meta.description,
    openGraph: { title: t.meta.title, description: t.meta.description, siteName: "VIMORA", type: "website" },
    alternates: { canonical: "/" },
    icons: { icon: "/icon.svg" },
  };
}

export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: light)", color: "#FAF8F5" }, { media: "(prefers-color-scheme: dark)", color: "#1B1815" }],
  width: "device-width",
  initialScale: 1,
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const { locale } = await getServerDict();
  const theme = (await cookies()).get("vimora_theme")?.value === "dark" ? "dark" : "light";
  return (
    <html lang={locale} data-theme={theme} className={`${GeistSans.variable} ${serif.variable}`} suppressHydrationWarning>
      <body className="min-h-dvh">
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded focus:bg-ink focus:px-3 focus:py-2 focus:text-ink-fg">Skip to content</a>
        <Providers locale={locale}>{children}</Providers>
      </body>
    </html>
  );
}
