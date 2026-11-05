import type { Metadata } from "next";
import { PolicyPage } from "@/features/policy-page";
import { getServerDict } from "@/lib/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.pages.servicePolicy, alternates: { canonical: "/service-policy" } };
}

export default function Page() {
  return <PolicyPage slug="service-policy" fallbackTitle={(t) => t.pages.servicePolicy} />;
}
