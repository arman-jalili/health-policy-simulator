"use client";

import { useSettings } from "@/components/providers";
import { CopyButton } from "@/components/ui/copy-button";

export function JsonBlock({
  value,
  summary,
  open = false,
}: {
  readonly value: unknown;
  readonly summary?: string;
  readonly open?: boolean;
}) {
  const { t } = useSettings();
  const text = JSON.stringify(value, null, 2);
  return (
    <details open={open} className="rounded-md border border-line bg-surface">
      <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-ink">
        {summary ?? t("common.details")}
      </summary>
      <div className="border-t border-line">
        <div className="flex justify-end px-2 py-1.5">
          <CopyButton value={text} />
        </div>
        <pre className="max-h-80 overflow-auto border-t border-line bg-surface-muted p-3 font-mono text-2xs leading-relaxed text-ink">
          {text}
        </pre>
      </div>
    </details>
  );
}
