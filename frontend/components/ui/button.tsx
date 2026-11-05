import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/format";

const button = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50 select-none",
  {
    variants: {
      variant: {
        primary: "bg-accent text-accent-fg shadow-[0_6px_16px_-8px_rgb(122_78_45/0.6)] hover:bg-accent-hover disabled:bg-raised disabled:text-muted disabled:shadow-none disabled:opacity-100",
        dark: "bg-ink text-ink-fg hover:bg-ink-hover disabled:opacity-60",
        secondary: "bg-raised text-fg hover:bg-border",
        outline: "border border-border bg-surface text-fg hover:border-fg/30 hover:bg-raised/40",
        ghost: "text-fg hover:bg-raised",
        danger: "border border-danger/40 bg-surface text-danger hover:bg-danger/5",
        link: "text-fg underline underline-offset-4 decoration-border hover:decoration-fg px-0 h-auto",
      },
      size: { sm: "h-8 px-3.5 text-[13px] rounded-full", md: "h-10 px-5 text-sm rounded-full", lg: "h-12 px-7 text-[15px] font-semibold rounded-full", icon: "h-9 w-9 rounded-full" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof button> & { asChild?: boolean; loading?: boolean };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({ className, variant, size, asChild, loading, children, disabled, ...props }, ref) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp ref={ref} className={cn(button({ variant, size }), className)} disabled={disabled || loading} aria-busy={loading || undefined} {...props}>
      {asChild ? children : (<>{loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}{children}</>)}
    </Comp>
  );
});
