import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  readonly loading?: boolean;
  readonly disabledReason?: string | undefined;
  readonly icon?: ReactNode;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "border-accent bg-accent text-on-accent hover:bg-accent-hover",
  secondary: "border-line-strong bg-surface text-ink hover:bg-surface-muted",
  ghost: "border-transparent bg-transparent text-ink-muted hover:bg-surface-muted hover:text-ink",
  danger: "border-danger bg-danger text-on-accent hover:opacity-90",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 px-2.5 text-2xs",
  md: "h-9 px-3 text-sm",
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  disabledReason,
  icon,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const isDisabled = disabled === true || loading || disabledReason !== undefined;
  return (
    <button
      type="button"
      disabled={isDisabled}
      title={disabledReason}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-2 rounded-md border font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    >
      {loading ? (
        <span
          aria-hidden="true"
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}
