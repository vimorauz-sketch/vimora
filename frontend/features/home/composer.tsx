"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/client";

/** The hero task composer. Sends the description to the AI assistant page. */
export function Composer() {
  const { t } = useI18n();
  const router = useRouter();
  const [text, setText] = useState("");
  return (
    <form
      className="card p-2.5 transition-shadow focus-within:shadow-[var(--shadow-lift)]"
      onSubmit={(e) => { e.preventDefault(); if (text.trim().length >= 2) router.push(`/assistant?q=${encodeURIComponent(text.trim())}`); }}
    >
      <label htmlFor="composer" className="sr-only">{t.home.composerLabel}</label>
      <textarea id="composer" value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={4000} placeholder={t.home.composerPlaceholder}
        onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) (e.currentTarget.form as HTMLFormElement).requestSubmit(); }}
        className="block w-full resize-none bg-transparent px-3 py-3 text-[16px] leading-relaxed placeholder:text-muted/70 focus:outline-none sm:text-[17px]" />
      <div className="flex flex-wrap items-center justify-between gap-3 px-3 pb-1.5">
        <p className="text-[13px] text-muted">{t.home.composerHint}</p>
        <Button type="submit" disabled={text.trim().length < 2}>{t.home.composerSubmit}</Button>
      </div>
    </form>
  );
}
