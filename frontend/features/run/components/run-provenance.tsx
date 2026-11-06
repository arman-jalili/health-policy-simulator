"use client";

import { useSettings } from "@/components/providers";
import { StatusPill } from "@/components/ui/status-pill";
import { engineKind, engineLabel } from "@/lib/engine";

/**
 * The caveat for a run the orchestrator drove.
 *
 * `scripted` is the engine, not the driver: a scripted run derives its stances from the persona cards
 * and writes `[synthetic] …` arguments, and the jury must not read that as a model's opinion.
 */
export function RunProvenanceBanner({
  automated,
  scripted,
}: {
  readonly automated: boolean;
  readonly scripted: boolean;
}) {
  const { t } = useSettings();
  if (!automated) return null;
  return (
    <div
      role="status"
      className="rounded-md border border-warn/40 bg-warn-quiet px-4 py-2 text-sm text-warn"
    >
      <p>{t("run.automatedBanner")}</p>
      {scripted && <p className="mt-1 text-2xs">{t("run.automatedScriptedHint")}</p>}
    </div>
  );
}

export function RunDriverBadge({
  automated,
  known,
}: {
  readonly automated: boolean;
  readonly known: boolean;
}) {
  const { t } = useSettings();
  if (!known) return null;
  return (
    <StatusPill tone={automated ? "warn" : "neutral"}>
      {automated ? t("run.driverAutomated") : t("run.driverManual")}
    </StatusPill>
  );
}

/**
 * Which engine wrote this run's turns — "Live-LLM" or "Skript (Platzhalter)".
 *
 * Deliberately no model id: the id changes with the provider and means nothing to the jury. The value
 * may be a model id or a provider name; only the kind is rendered.
 */
export function RunModelBadge({ model }: { readonly model: string | null }) {
  const { locale } = useSettings();
  const label = engineLabel(model, locale);
  if (label === "") return null;
  return (
    <StatusPill tone={engineKind(model) === "scripted" ? "warn" : "ok"}>{label}</StatusPill>
  );
}
