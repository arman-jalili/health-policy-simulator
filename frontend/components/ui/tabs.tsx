"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSettings } from "@/components/providers";
import { cn } from "@/lib/cn";
import type { MessageKey } from "@/lib/i18n";

export interface TabItem {
  readonly href: string;
  readonly labelKey: MessageKey;
  readonly exact?: boolean;
}

export function Tabs({ items }: { readonly items: readonly TabItem[] }) {
  const pathname = usePathname();
  const { t } = useSettings();
  return (
    <nav aria-label={t("run.tabs.console")} className="border-b border-line">
      <ul className="flex gap-0 overflow-x-auto">
        {items.map((item) => {
          const active =
            item.exact === true ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex h-11 items-center whitespace-nowrap border-b-[3px] px-3 font-heading text-[0.8125rem] font-bold uppercase tracking-[0.04em] no-underline transition-colors",
                  active
                    ? "border-accent text-accent"
                    : "border-transparent text-ink-muted hover:text-accent",
                )}
              >
                {t(item.labelKey)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
