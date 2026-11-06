import type { ReactNode, ThHTMLAttributes, TdHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export function TableWrap({ children, className }: { readonly children: ReactNode; readonly className?: string }) {
  return <div className={cn("overflow-x-auto rounded-md border border-line bg-surface", className)}>{children}</div>;
}

export function Table({ children, caption }: { readonly children: ReactNode; readonly caption?: string }) {
  return (
    <table className="w-full border-collapse text-sm">
      {caption !== undefined && <caption className="sr-only">{caption}</caption>}
      {children}
    </table>
  );
}

export function THead({ children }: { readonly children: ReactNode }) {
  return <thead className="bg-surface-muted text-left text-2xs font-semibold uppercase tracking-wide text-ink-muted">{children}</thead>;
}

export function TBody({ children }: { readonly children: ReactNode }) {
  return <tbody className="divide-y divide-line">{children}</tbody>;
}

export function TR({ children, className }: { readonly children: ReactNode; readonly className?: string }) {
  return <tr className={cn("align-top", className)}>{children}</tr>;
}

export function TH({ children, className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th scope="col" className={cn("whitespace-nowrap px-3 py-2 font-semibold", className)} {...props}>
      {children}
    </th>
  );
}

export function TD({ children, className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("px-3 py-2", className)} {...props}>
      {children}
    </td>
  );
}

export function EmptyRow({ colSpan, children }: { readonly colSpan: number; readonly children: ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-6 text-center text-sm text-ink-muted">
        {children}
      </td>
    </tr>
  );
}
