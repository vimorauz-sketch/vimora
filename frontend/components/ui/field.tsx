import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/format";

export const control = "w-full rounded-[10px] border border-border bg-surface px-3 text-[14px] text-fg placeholder:text-muted/70 transition-colors hover:border-fg/30 focus:border-accent/60 focus:outline-none focus:ring-4 focus:ring-accent/10 aria-[invalid=true]:border-danger disabled:opacity-60";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...p }, ref) {
  return <input ref={ref} className={cn(control, "h-10", className)} {...p} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...p }, ref) {
  return <textarea ref={ref} className={cn(control, "min-h-[112px] py-2.5 leading-relaxed", className)} {...p} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select({ className, children, ...p }, ref) {
  return (
    <select ref={ref} className={cn(control, "h-10 appearance-none bg-[length:16px] bg-[right_10px_center] bg-no-repeat pr-9", className)}
      style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23a5a49b' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")" }} {...p}>
      {children}
    </select>
  );
});

type FieldProps = { label: ReactNode; hint?: ReactNode; error?: string; children: (id: string, describedBy?: string) => ReactNode; optional?: string; className?: string };

/** Label + control + hint/error with correct aria wiring. */
export function Field({ label, hint, error, children, optional, className }: FieldProps) {
  const id = useId();
  const descId = hint || error ? `${id}-desc` : undefined;
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={id} className="block text-[13px] font-medium text-fg">
        {label}
        {optional && <span className="ml-1.5 font-normal text-muted">({optional})</span>}
      </label>
      {children(id, descId)}
      {(error || hint) && (
        <p id={descId} className={cn("text-[12.5px]", error ? "text-danger" : "text-muted")} role={error ? "alert" : undefined}>
          {error || hint}
        </p>
      )}
    </div>
  );
}

export function Checkbox({ label, ...p }: InputHTMLAttributes<HTMLInputElement> & { label: ReactNode }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 text-[14px]">
      <input type="checkbox" className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-[var(--accent)]" {...p} />
      <span>{label}</span>
    </label>
  );
}
