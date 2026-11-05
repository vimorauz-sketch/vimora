import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell, ForgotForm } from "@/features/auth/forms";
import { getServerDict } from "@/lib/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getServerDict();
  return { title: t.auth.forgotTitle, robots: { index: false } };
}

export default async function Page() {
  const { t } = await getServerDict();
  return (
    <AuthShell title={t.auth.forgotTitle} sub={t.auth.forgotSub}>
      <Suspense><ForgotForm /></Suspense>
    </AuthShell>
  );
}
