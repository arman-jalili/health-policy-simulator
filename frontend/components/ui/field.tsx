import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

import { cn } from "@/lib/cn";

const CONTROL =
  "w-full rounded-xs border border-line-strong bg-surface px-3 text-sm text-ink placeholder:text-ink-subtle focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent disabled:bg-surface-muted disabled:text-ink-subtle";

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  readonly label: string;
  readonly htmlFor: string;
  readonly hint?: string | undefined;
  readonly error?: string | undefined;
  readonly children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="block font-heading text-sm font-medium text-ink">
        {label}
      </label>
      {children}
      {hint !== undefined && (
        <p id={`${htmlFor}-hint`} className="text-2xs text-ink-muted">
          {hint}
        </p>
      )}
      {error !== undefined && (
        <p id={`${htmlFor}-error`} role="alert" className="text-2xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(CONTROL, "h-10", className)} {...props} />;
}

export function TextArea({ className, rows = 4, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea rows={rows} className={cn(CONTROL, "py-2", className)} {...props} />;
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(CONTROL, "h-10", className)} {...props}>
      {children}
    </select>
  );
}

export function Checkbox({
  className,
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { readonly label: string }) {
  return (
    <label className={cn("flex items-center gap-2 text-sm text-ink", className)}>
      <input
        type="checkbox"
        className="h-4 w-4 rounded-xs border-line-strong accent-accent"
        {...props}
      />
      <span>{label}</span>
    </label>
  );
}

export const controlClass = CONTROL;
