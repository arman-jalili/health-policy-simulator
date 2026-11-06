"use client";

import { useId, useState } from "react";

import { useSettings } from "@/components/providers";
import { cn } from "@/lib/cn";

const CLAMP = {
  3: "line-clamp-3",
  4: "line-clamp-4",
  5: "line-clamp-5",
} as const;

export function ExpandableText({
  text,
  collapsedLines = 4,
  className,
}: {
  readonly text: string;
  readonly collapsedLines?: keyof typeof CLAMP;
  readonly className?: string;
}) {
  const { t } = useSettings();
  const [expanded, setExpanded] = useState(false);
  const textId = useId();
  const long = text.length > 280;

  return (
    <div className={cn("min-w-0", className)}>
      <p
        id={textId}
        className={cn("text-sm leading-relaxed text-ink", !expanded && CLAMP[collapsedLines])}
      >
        {text}
      </p>
      {long && (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          aria-controls={textId}
          className="mt-1.5 font-heading text-2xs font-bold uppercase tracking-[0.04em] text-accent hover:underline"
        >
          {expanded ? t("common.less") : t("common.more")}
        </button>
      )}
    </div>
  );
}
