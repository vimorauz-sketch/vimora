"use client";

import { Input } from "@/components/ui/field";
import { fromMinor, toMinor } from "@/lib/format";
import { useEffect, useState } from "react";

/** Major-unit text input bound to an integer minor-unit value (no float math). */
export function MoneyInput({ value, onChange, id, ...rest }: { value: number; onChange: (minor: number) => void; id?: string; "aria-label"?: string; className?: string }) {
  const [text, setText] = useState(fromMinor(value));
  useEffect(() => { if (toMinor(text) !== value) setText(fromMinor(value)); }, [value]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Input id={id} inputMode="decimal" value={text} {...rest}
      aria-invalid={toMinor(text) === null}
      onChange={(e) => { setText(e.target.value); const m = toMinor(e.target.value); if (m !== null) onChange(m); }} />
  );
}
