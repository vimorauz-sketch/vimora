"use client";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  const { t } = useI18n();
  return (
    <main id="main" className="mx-auto flex min-h-[70dvh] max-w-[720px] flex-col justify-center px-6">
      <p className="display text-[96px] text-muted/40">500</p>
      <h1 className="display mt-2 text-[30px]">{t.pages.serverError}</h1>
      <p className="mt-3 text-muted">{t.pages.serverErrorBody}</p>
      <div className="mt-8 flex gap-3"><Button onClick={reset}>{t.common.retry}</Button><Button asChild variant="outline"><a href="/">{t.pages.home}</a></Button></div>
    </main>
  );
}
