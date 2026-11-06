import Link from "next/link";
import type { ReactNode } from "react";

interface Crumb {
  readonly label: string;
  readonly href?: string;
}

export function PageHeader({
  title,
  subtitle,
  crumbs,
  actions,
  meta,
}: {
  readonly title: string;
  readonly subtitle?: string | undefined;
  readonly crumbs?: readonly Crumb[] | undefined;
  readonly actions?: ReactNode;
  readonly meta?: ReactNode;
}) {
  return (
    <header className="mb-6 border-b border-line pb-5">
      {crumbs !== undefined && crumbs.length > 0 && (
        <nav aria-label="Brotkrümel" className="mb-3 text-2xs text-ink-muted">
          <ol className="flex flex-wrap items-center gap-1.5">
            {crumbs.map((crumb, index) => (
              <li key={`${crumb.label}-${index}`} className="flex items-center gap-1.5">
                {index > 0 && (
                  <span aria-hidden="true" className="text-ink-subtle">
                    /
                  </span>
                )}
                {crumb.href !== undefined ? (
                  <Link href={crumb.href} className="no-underline hover:underline">
                    {crumb.label}
                  </Link>
                ) : (
                  <span aria-current="page">{crumb.label}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl">{title}</h1>
          {subtitle !== undefined && (
            <p className="mt-2 max-w-prose text-base text-ink-muted">{subtitle}</p>
          )}
        </div>
        {actions !== undefined && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {meta !== undefined && <div className="mt-3">{meta}</div>}
    </header>
  );
}
