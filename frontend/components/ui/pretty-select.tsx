"use client";

import * as RS from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/format";

export type PrettyOption = { value: string; label: string; hint?: string; icon?: ReactNode; disabled?: boolean; badge?: string };

/**
 * Rounded, theme-aware dropdown (replaces the browser's square native list).
 * Keyboard: arrows / type-ahead / Enter / Esc — handled by Radix Select.
 */
export function PrettySelect({
  value, onValueChange, options, placeholder, icon, id, className, "aria-label": ariaLabel, "aria-invalid": invalid, size = "md", disabled,
}: {
  value: string | null | undefined; onValueChange: (v: string) => void; options: PrettyOption[]; placeholder?: string; icon?: ReactNode; id?: string;
  className?: string; "aria-label"?: string; "aria-invalid"?: boolean; size?: "md" | "lg"; disabled?: boolean;
}) {
  const current = options.find((o) => o.value === value);
  return (
    <RS.Root value={value || undefined} onValueChange={onValueChange} disabled={disabled}>
      <RS.Trigger id={id} aria-label={ariaLabel} aria-invalid={invalid}
        className={cn(
          "group flex w-full items-center gap-2.5 rounded-[14px] border border-border bg-surface px-3.5 text-left text-[14px] text-fg shadow-[0_1px_0_rgb(0_0_0/0.02)] transition-all",
          "hover:border-accent/50 focus:outline-none focus-visible:border-accent/60 focus-visible:ring-4 focus-visible:ring-accent/10 data-[state=open]:border-accent/60 data-[state=open]:ring-4 data-[state=open]:ring-accent/10",
          "aria-[invalid=true]:border-danger disabled:opacity-60",
          size === "lg" ? "h-12" : "h-11",
          className,
        )}>
        {(current?.icon ?? icon) && <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-tint-0 text-accent [&>svg]:h-4 [&>svg]:w-4">{current?.icon ?? icon}</span>}
        <span className={cn("min-w-0 flex-1 truncate", !current && "text-muted")}><RS.Value placeholder={placeholder} /></span>
        <RS.Icon asChild><ChevronDown className="h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-data-[state=open]:rotate-180" aria-hidden /></RS.Icon>
      </RS.Trigger>
      <RS.Portal>
        <RS.Content position="popper" sideOffset={8} collisionPadding={12}
          className="z-[60] max-h-[min(380px,var(--radix-select-content-available-height))] w-[var(--radix-select-trigger-width)] min-w-[220px] overflow-hidden rounded-[18px] border border-border bg-surface p-1.5 shadow-[var(--shadow-lift)] data-[state=open]:animate-[vimora-pop_.18s_ease-out]">
          <RS.Viewport>
            {options.map((o) => (
              <RS.Item key={o.value} value={o.value} disabled={o.disabled}
                className="relative flex cursor-pointer select-none items-center gap-3 rounded-[12px] px-3 py-2.5 text-[14px] text-fg outline-none transition-colors data-[disabled]:cursor-not-allowed data-[disabled]:opacity-45 data-[highlighted]:bg-raised data-[state=checked]:bg-tint-0/70">
                {o.icon && <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-raised text-accent [&>svg]:h-4 [&>svg]:w-4">{o.icon}</span>}
                <span className="min-w-0 flex-1">
                  <RS.ItemText>{o.label}</RS.ItemText>
                  {o.hint && <span className="block truncate text-[12px] text-muted">{o.hint}</span>}
                </span>
                {o.badge && <span className="rounded-full bg-tint-1 px-2 py-0.5 text-[11px] font-medium text-ok">{o.badge}</span>}
                <RS.ItemIndicator><Check className="h-4 w-4 text-accent" aria-hidden /></RS.ItemIndicator>
              </RS.Item>
            ))}
          </RS.Viewport>
        </RS.Content>
      </RS.Portal>
    </RS.Root>
  );
}
