import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type StatusTone = "ok" | "warn" | "danger" | "info" | "neutral" | "veto";

const TONES: Record<StatusTone, string> = {
  ok: "border-ok/30 bg-ok-quiet text-ok",
  warn: "border-warn/30 bg-warn-quiet text-warn",
  danger: "border-danger/30 bg-danger-quiet text-danger",
  info: "border-info/30 bg-info-quiet text-info",
  neutral: "border-line bg-surface-muted text-ink-muted",
  veto: "border-veto/30 bg-veto-quiet text-veto",
};

export function StatusPill({
  tone = "neutral",
  children,
  className,
}: {
  readonly tone?: StatusTone;
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-xs border px-1.5 py-0.5 text-2xs font-medium whitespace-nowrap",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
