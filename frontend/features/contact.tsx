"use client";

import { useForm } from "react-hook-form";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/field";
import { ErrorState, Notice } from "@/components/ui/misc";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/client";

type F = { name: string; email: string; subject: string; message: string; website: string };

export function ContactForm() {
  const { t } = useI18n();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<F>({ defaultValues: { website: "" } });
  if (sent) return <Notice tone="accent">{t.pages.sent}</Notice>;
  return (
    <form className="space-y-5" onSubmit={form.handleSubmit(async (v) => {
      setError(null);
      try { await api("/contact", { body: v }); setSent(true); } catch (e) { setError(errorMessage(e, t)); }
    })}>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t.pages.name}>{(id) => <Input id={id} autoComplete="name" {...form.register("name", { required: true, maxLength: 200 })} />}</Field>
        <Field label="Email">{(id) => <Input id={id} type="email" autoComplete="email" {...form.register("email", { required: true })} />}</Field>
      </div>
      <Field label={t.pages.subject}>{(id) => <Input id={id} {...form.register("subject", { required: true, maxLength: 200 })} />}</Field>
      <Field label={t.pages.message}>{(id) => <Textarea id={id} rows={6} {...form.register("message", { required: true, minLength: 10, maxLength: 5000 })} />}</Field>
      {/* honeypot for bots; hidden from people and assistive tech */}
      <input type="text" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden {...form.register("website")} />
      {error && <ErrorState message={error} />}
      <Button type="submit" loading={form.formState.isSubmitting}>{t.pages.sendMessage}</Button>
    </form>
  );
}
