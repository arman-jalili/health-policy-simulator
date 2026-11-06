"use client";

import type { ReactNode } from "react";

import { useSettings } from "@/components/providers";

export function ChartFrame({
  title,
  description,
  children,
  table,
}: {
  readonly title: string;
  readonly description?: string | undefined;
  readonly children: ReactNode;
  readonly table: ReactNode;
}) {
  const { t } = useSettings();
  return (
    <figure className="space-y-2">
      <figcaption className="text-sm font-medium text-ink">{title}</figcaption>
      {description !== undefined && <p className="text-2xs text-ink-muted">{description}</p>}
      <div>{children}</div>
      <details className="rounded-md border border-line bg-surface">
        <summary className="cursor-pointer px-3 py-2 text-2xs text-ink-muted">
          {t("common.showData")}
        </summary>
        <div className="overflow-x-auto border-t border-line">{table}</div>
      </details>
    </figure>
  );
}
