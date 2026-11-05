import type { Metadata } from "next";
import { Suspense } from "react";
import { AssistantChat } from "@/features/assistant";
import { getServerDict } from "@/lib/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.assistant.title, description: t.assistant.sub, alternates: { canonical: "/assistant" } };
}

export default async function AssistantPage() {
  const { t } = await getServerDict();
  return (
    <div className="mx-auto max-w-[860px] px-5 py-14 sm:px-8">
      <h1 className="display text-[32px] sm:text-[44px]">{t.assistant.title}</h1>
      <p className="mt-3 max-w-[60ch] text-muted">{t.assistant.sub}</p>
      <Suspense><AssistantChat /></Suspense>
    </div>
  );
}
