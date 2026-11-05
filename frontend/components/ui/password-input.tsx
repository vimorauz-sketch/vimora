"use client";

import { Eye, EyeOff } from "lucide-react";
import { forwardRef, useState, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import { control } from "./field";

/** Password field with a show / hide button (eye icon). */
export const PasswordInput = forwardRef<HTMLInputElement, Omit<InputHTMLAttributes<HTMLInputElement>, "type">>(function PasswordInput({ className, ...p }, ref) {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);
  const label = visible ? t.auth.hidePassword : t.auth.showPassword;
  return (
    <div className="relative">
      <input ref={ref} type={visible ? "text" : "password"} spellCheck={false} autoCapitalize="off" className={cn(control, "h-10 pr-11", className)} {...p} />
      <button type="button" onClick={() => setVisible((v) => !v)} aria-label={label} aria-pressed={visible} title={label}
        className="absolute right-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-full text-muted transition-colors hover:bg-raised hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50">
        {visible ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
      </button>
    </div>
  );
});
