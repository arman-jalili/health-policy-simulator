"use client";

import { useSettings } from "@/components/providers";
import { StatusPill, type StatusTone } from "@/components/ui/status-pill";
import { stanceSymbol } from "@/lib/chart/encoding";
import { enumLabel } from "@/lib/i18n";

const TONES: Record<string, StatusTone> = {
  support: "ok",
  oppose: "danger",
  qualify: "warn",
  conditional_accept: "info",
  abstain: "neutral",
};

export function StanceBadge({ stance }: { readonly stance: string }) {
  const { locale } = useSettings();
  return (
    <StatusPill tone={TONES[stance] ?? "neutral"}>
      <span aria-hidden="true">{stanceSymbol(stance)}</span>
      {enumLabel("stance", stance, locale)}
    </StatusPill>
  );
}
