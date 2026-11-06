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
      <ul className="flex gap-1 overflow-x-auto">
        {items.map((item) => {
          const active =
            item.exact === true ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex h-10 items-center whitespace-nowrap border-b-2 px-3 text-sm no-underline",
                  active
                    ? "border-accent font-semibold text-accent"
                    : "border-transparent text-ink-muted hover:text-ink",
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
