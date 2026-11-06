import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Card({ children, className }: { readonly children: ReactNode; readonly className?: string }) {
  return (
    <section className={cn("rounded-md border border-line bg-surface", className)}>{children}</section>
  );
}

export function CardHeader({
  title,
  description,
  actions,
  id,
}: {
  readonly title: string;
  readonly description?: string | undefined;
  readonly actions?: ReactNode;
  readonly id?: string | undefined;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
      <div className="min-w-0">
        <h2 id={id} className="text-base font-semibold">
          {title}
        </h2>
        {description !== undefined && <p className="mt-1 text-sm text-ink-muted">{description}</p>}
      </div>
      {actions !== undefined && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function CardBody({ children, className }: { readonly children: ReactNode; readonly className?: string }) {
  return <div className={cn("px-4 py-3", className)}>{children}</div>;
}
