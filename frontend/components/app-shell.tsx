"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Icon, type IconName } from "@/components/icons";
import { useSettings } from "@/components/providers";
import { ReadinessBanner } from "@/components/readiness-banner";
import { cn } from "@/lib/cn";
import type { MessageKey } from "@/lib/i18n";

interface NavItem {
  readonly href: string;
  readonly labelKey: MessageKey;
  readonly icon: IconName;
  readonly exact?: boolean;
}

const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", labelKey: "nav.overview", icon: "overview", exact: true },
  { href: "/runs/new", labelKey: "nav.newRun", icon: "plus" },
  { href: "/stakeholders", labelKey: "nav.stakeholders", icon: "building" },
  { href: "/claims", labelKey: "nav.claims", icon: "shield" },
  { href: "/health", labelKey: "nav.health", icon: "pulse" },
  { href: "/settings", labelKey: "nav.settings", icon: "sliders" },
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact === true) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function AppShell({ children }: { readonly children: ReactNode }) {
  const { t } = useSettings();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <div className="min-h-dvh bg-surface-muted">
      <a href="#main" className="skip-link">
        {t("nav.skip")}
      </a>
      <div className="flex min-h-dvh">
        <aside
          className={cn(
            "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-line bg-surface lg:flex",
            collapsed ? "w-16" : "w-60",
          )}
        >
          <div className="flex h-16 items-center gap-3 border-b border-line px-4">
            <Link
              href="/"
              className="flex min-w-0 items-center gap-2 text-ink no-underline"
              aria-label={t("app.name")}
            >
              <span
                aria-hidden="true"
                className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-accent text-sm font-semibold text-on-accent"
              >
                HP
              </span>
              {!collapsed && (
                <span className="truncate text-sm font-semibold leading-tight">{t("app.name")}</span>
              )}
            </Link>
          </div>
          <nav aria-label={t("nav.main")} className="flex flex-1 flex-col gap-1 p-2">
            {NAV_ITEMS.map((item) => {
              const active = isActive(pathname, item);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  title={collapsed ? t(item.labelKey) : undefined}
                  className={cn(
                    "flex h-10 items-center gap-3 rounded-md px-3 text-sm no-underline",
                    active
                      ? "bg-accent-quiet font-semibold text-accent"
                      : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                    collapsed && "justify-center px-0",
                  )}
                >
                  <Icon name={item.icon} />
                  {!collapsed && <span className="truncate">{t(item.labelKey)}</span>}
                </Link>
              );
            })}
          </nav>
          <div className="border-t border-line p-2">
            <button
              type="button"
              onClick={() => setCollapsed((value) => !value)}
              aria-label={collapsed ? t("nav.expand") : t("nav.collapse")}
              className="flex h-10 w-full items-center justify-center rounded-md text-ink-muted hover:bg-surface-muted hover:text-ink"
            >
              <Icon name={collapsed ? "chevron-right" : "chevron-left"} />
            </button>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur-none lg:hidden">
            <div className="flex h-14 items-center gap-3 px-4">
              <button
                type="button"
                onClick={() => setMobileOpen((value) => !value)}
                aria-label={t("nav.main")}
                aria-expanded={mobileOpen}
                className="grid h-9 w-9 place-items-center rounded-md border border-line text-ink-muted"
              >
                <Icon name={mobileOpen ? "close" : "menu"} />
              </button>
              <span className="truncate text-sm font-semibold">{t("app.name")}</span>
            </div>
            {mobileOpen && (
              <nav aria-label={t("nav.main")} className="border-t border-line bg-surface p-2">
                {NAV_ITEMS.map((item) => {
                  const active = isActive(pathname, item);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex h-10 items-center gap-3 rounded-md px-3 text-sm no-underline",
                        active
                          ? "bg-accent-quiet font-semibold text-accent"
                          : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                      )}
                    >
                      <Icon name={item.icon} />
                      <span>{t(item.labelKey)}</span>
                    </Link>
                  );
                })}
              </nav>
            )}
          </header>
          <main id="main" className="mx-auto w-full max-w-content flex-1 px-4 py-6 lg:px-8">
            <ReadinessBanner />
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
