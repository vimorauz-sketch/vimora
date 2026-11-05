"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/field";
import { ErrorState } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { useArea } from "@/lib/area";
import { money } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";

type Suggestion = { slug: string; name: string; category: string; price: { type: string; amount_minor?: number; currency?: string; unit?: string | null } | null; estimated_delivery: string };
type Reply = {
  ai_available: boolean; reply: string | null; suggestions: Suggestion[]; recommend_custom_order: boolean; complexity?: "low" | "medium" | "high" | null;
  clarifying_questions?: string[]; missing_information?: string[]; required_information?: string[]; indicative_price?: Suggestion["price"];
};
type Turn = { role: "user" | "assistant"; content: string; data?: Reply };

export function AssistantChat() {
  const { t, locale } = useI18n();
  const { area } = useArea();
  const params = useSearchParams();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function send(message: string) {
    const msg = message.trim();
    if (msg.length < 2 || busy) return;
    const history = turns.map((x) => ({ role: x.role, content: x.content }));
    setTurns((v) => [...v, { role: "user", content: msg }]);
    setText("");
    setBusy(true);
    setError(null);
    try {
      const data = await api<Reply>("/ai/assist", { body: { message: msg, history, language: locale, area: area ?? undefined } });
      setTurns((v) => [...v, { role: "assistant", content: data.reply ?? t.assistant.unavailable, data }]);
    } catch (e) {
      setError(errorMessage(e, t));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const q = params.get("q");
    if (q && !started.current) { started.current = true; void send(q); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns.length]);

  const firstUser = turns.find((x) => x.role === "user")?.content ?? "";
  return (
    <div className="mt-10">
      <div className="space-y-6" aria-live="polite">
        {turns.length === 0 && !busy && <p className="text-muted">{t.assistant.empty}</p>}
        {turns.map((turn, i) => turn.role === "user" ? (
          <div key={i} className="ml-auto max-w-[85%] rounded-[10px] bg-raised px-4 py-3">{turn.content}</div>
        ) : (
          <div key={i} className="max-w-[92%] space-y-4 border-l-2 border-accent pl-5">
            <p className="whitespace-pre-line">{turn.data?.ai_available === false ? t.assistant.unavailable : turn.content}</p>
            {turn.data && <ReplyDetails data={turn.data} firstMessage={firstUser} />}
          </div>
        ))}
        {busy && <p className="text-muted" role="status">{t.assistant.thinking}</p>}
        {error && <ErrorState message={error} />}
        <div ref={endRef} />
      </div>
      <form className="mt-8 rounded-[12px] border border-border bg-surface p-2" onSubmit={(e) => { e.preventDefault(); void send(text); }}>
        <label htmlFor="assist" className="sr-only">{t.assistant.placeholder}</label>
        <Textarea id="assist" value={text} onChange={(e) => setText(e.target.value)} placeholder={t.assistant.placeholder} maxLength={4000} rows={3}
          className="border-0 bg-transparent focus:border-0" onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(text); } }} />
        <div className="flex items-center justify-between gap-3 px-2 pb-1">
          <p className="text-[12.5px] text-muted">{t.assistant.disclaimer}</p>
          <Button type="submit" loading={busy} disabled={text.trim().length < 2}>{t.assistant.send}</Button>
        </div>
      </form>
    </div>
  );
}

function ReplyDetails({ data, firstMessage }: { data: Reply; firstMessage: string }) {
  const { t, locale } = useI18n();
  const lists: [string, string[] | undefined][] = [[t.assistant.questions, data.clarifying_questions], [t.assistant.missing, data.missing_information], [t.assistant.prepare, data.required_information]];
  return (
    <div className="space-y-4 text-[14px]">
      {data.complexity && <p><span className="text-muted">{t.assistant.complexity}: </span>{t.assistant[data.complexity]}</p>}
      {lists.map(([title, items]) => items && items.length > 0 && (
        <div key={title}><p className="font-medium">{title}</p><ul className="mt-1.5 list-disc space-y-1 pl-5 text-muted">{items.map((q) => <li key={q}>{q}</li>)}</ul></div>
      ))}
      {data.suggestions.length > 0 && (
        <div>
          <p className="font-medium">{t.assistant.suggested}</p>
          <div className="mt-2 space-y-2">
            {data.suggestions.map((s) => (
              <Link key={s.slug} href={`/services/${s.slug}`} className="flex items-center justify-between gap-4 rounded-[8px] border border-border px-4 py-3 hover:border-fg/40">
                <span className="font-medium">{s.name}</span>
                <span className="tabular-nums text-muted">{s.price?.amount_minor !== undefined && s.price.currency ? money(s.price.amount_minor, s.price.currency, locale) : t.services.customQuote}</span>
              </Link>
            ))}
          </div>
          {data.indicative_price && <p className="mt-2 text-[12.5px] text-muted">{t.assistant.indicative}</p>}
        </div>
      )}
      {data.recommend_custom_order && (
        <Button asChild variant="outline" size="sm"><Link href={`/custom-order?d=${encodeURIComponent(firstMessage.slice(0, 1500))}`}>{t.assistant.customCta}</Link></Button>
      )}
    </div>
  );
}
