"use client";

import { useSettings } from "@/components/providers";
import { StatusPill } from "@/components/ui/status-pill";

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
