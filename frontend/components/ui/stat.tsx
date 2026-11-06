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
    <div className="rounded-md border border-line bg-surface px-3 py-2">
      <dt className="text-2xs uppercase tracking-wide text-ink-muted">{label}</dt>
      <dd className="mt-1 text-lg font-semibold tabular">{value}</dd>
      {hint !== undefined && <p className="mt-1 text-2xs text-ink-subtle">{hint}</p>}
    </div>
  );
}
