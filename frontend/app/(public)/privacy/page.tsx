import type { Metadata } from "next";
import { PolicyPage } from "@/features/policy-page";
import { getServerDict } from "@/lib/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.pages.privacy, alternates: { canonical: "/privacy" } };
}

export default function Page() {
  return <PolicyPage slug="privacy" fallbackTitle={(t) => t.pages.privacy} />;
}
