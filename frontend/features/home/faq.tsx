"use client";

import * as Accordion from "@radix-ui/react-accordion";
import { Plus } from "lucide-react";

export function FaqList({ items }: { items: { id: number; question: string; answer: string }[] }) {
  return (
    <Accordion.Root type="single" collapsible className="divide-y divide-border border-y border-border">
      {items.map((f) => (
        <Accordion.Item key={f.id} value={String(f.id)}>
          <Accordion.Header>
            <Accordion.Trigger className="group flex w-full items-center justify-between gap-6 py-5 text-left font-[family-name:var(--font-display)] text-[18px] text-ink">
              {f.question}
              <Plus className="h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-data-[state=open]:rotate-45" aria-hidden />
            </Accordion.Trigger>
          </Accordion.Header>
          <Accordion.Content className="pb-5 pr-10 text-muted"><p className="max-w-[68ch]">{f.answer}</p></Accordion.Content>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
}
