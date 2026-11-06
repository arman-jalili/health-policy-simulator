import type { ReactNode } from "react";

export function Stat({
  label,
  value,
  hint,
}: {
  readonly label: string;
  readonly value: ReactNode;
  readonly hint?: string | undefined;
}) {
  return (
    <div className="border border-line bg-surface px-4 py-3">
      <dt className="font-heading text-2xs font-bold uppercase tracking-[0.06em] text-ink-muted">
        {label}
      </dt>
      <dd className="mt-1 font-heading text-xl font-semibold tabular text-ink">{value}</dd>
      {hint !== undefined && <p className="mt-1 text-2xs text-ink-subtle">{hint}</p>}
    </div>
  );
}
