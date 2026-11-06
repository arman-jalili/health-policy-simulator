"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { BrandMark } from "@/components/brand-mark";
import { Icon } from "@/components/icons";
import { useSettings } from "@/components/providers";
import { ReadinessBanner } from "@/components/readiness-banner";
import { cn } from "@/lib/cn";
import type { MessageKey } from "@/lib/i18n";

interface NavItem {
  readonly href: string;
  readonly labelKey: MessageKey;
  readonly exact?: boolean;
  readonly match?: string;
}

const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", labelKey: "nav.overview", exact: true },
  { href: "/runs/new", labelKey: "nav.newRun", match: "/runs" },
  { href: "/stakeholders", labelKey: "nav.stakeholders" },
  { href: "/claims", labelKey: "nav.claims" },
  { href: "/health", labelKey: "nav.health" },
  { href: "/settings", labelKey: "nav.settings" },
];

interface NavGroup {
  readonly titleKey: MessageKey;
  readonly items: readonly NavItem[];
}

const SIDEBAR_GROUPS: readonly NavGroup[] = [
  {
    titleKey: "sidebar.runs",
    items: [
      { href: "/", labelKey: "nav.overview", exact: true },
      { href: "/runs/new", labelKey: "nav.newRun", match: "/runs" },
    ],
  },
  {
    titleKey: "sidebar.evidence",
    items: [
      { href: "/stakeholders", labelKey: "nav.stakeholders" },
      { href: "/claims", labelKey: "nav.claims" },
    ],
  },
  {
    titleKey: "sidebar.system",
    items: [
      { href: "/health", labelKey: "nav.health" },
      { href: "/settings", labelKey: "nav.settings" },
    ],
  },
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.match !== undefined) return pathname === item.match || pathname.startsWith(`${item.match}/`);
  if (item.exact === true) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function LocaleSwitch() {
  const { settings, updateSettings } = useSettings();
  return (
    <div className="flex items-center" aria-label="Sprache">
      {(["de-AT", "en"] as const).map((locale) => {
        const active = settings.locale === locale;
        return (
          <button
            key={locale}
            type="button"
            onClick={() => updateSettings({ locale })}
            aria-pressed={active}
            className={cn(
              "h-6 border px-2 font-heading text-2xs font-bold uppercase tracking-[0.06em] transition-colors",
              active
                ? "border-accent bg-accent text-on-accent"
                : "border-line-strong bg-surface text-ink-muted hover:border-accent hover:text-accent",
            )}
          >
            {locale === "de-AT" ? "DE" : "EN"}
          </button>
        );
      })}
    </div>
  );
}

function SidebarGroup({ group, pathname }: { readonly group: NavGroup; readonly pathname: string }) {
  const { t } = useSettings();
  return (
    <details open className="portal-tree group py-2 first:pt-0">
      <summary className="flex cursor-pointer items-center gap-2 py-1.5 font-heading text-sm font-bold uppercase tracking-[0.06em] text-ink transition-colors hover:text-accent">
        <span aria-hidden="true" className="w-4 text-center text-base font-normal text-ink-muted">
          <span className="group-open:hidden">+</span>
          <span className="hidden group-open:inline">−</span>
        </span>
        {t(group.titleKey)}
      </summary>
      <ul className="mt-1 space-y-0.5 pl-6">
        {group.items.map((item) => {
          const active = isActive(pathname, item);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "block py-1.5 text-[0.9375rem] leading-snug no-underline transition-colors",
                  active ? "font-medium text-accent" : "text-ink hover:text-accent",
                )}
              >
                {t(item.labelKey)}
              </Link>
            </li>
          );
        })}
      </ul>
    </details>
  );
}

export function AppShell({ children }: { readonly children: ReactNode }) {
  const { t } = useSettings();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [lookup, setLookup] = useState("");

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  function onLookup(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const value = lookup.trim();
    if (value === "") return;
    router.push(`/runs/${encodeURIComponent(value)}`);
  }

  return (
    <div id="top" className="flex min-h-dvh flex-col bg-surface">
      <a href="#main" className="skip-link">
        {t("nav.skip")}
      </a>

      {/* Utility bar */}
      <div className="border-b border-line bg-surface">
        <div className="mx-auto flex h-10 w-full max-w-content items-center justify-between gap-4 px-4 lg:px-6">
          <p className="truncate font-heading text-2xs font-medium uppercase tracking-[0.06em] text-ink-muted">
            {t("header.prototype")}
          </p>
          <div className="flex items-center gap-4">
            <LocaleSwitch />
            <Link
              href="/health"
              className="hidden font-heading text-2xs font-bold uppercase tracking-[0.06em] text-ink-muted no-underline hover:text-accent sm:inline"
            >
              {t("nav.health")}
            </Link>
            <Link
              href="/settings"
              className="hidden font-heading text-2xs font-bold uppercase tracking-[0.06em] text-ink-muted no-underline hover:text-accent sm:inline"
            >
              {t("nav.settings")}
            </Link>
          </div>
        </div>
      </div>

      {/* Brand header */}
      <header className="border-b border-line bg-surface">
        <div className="mx-auto w-full max-w-content px-4 py-5 lg:px-6">
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center gap-4 text-ink no-underline">
              <span aria-hidden="true">
                <BrandMark className="h-14 w-14 lg:h-16 lg:w-16" />
              </span>
              <span className="block w-32 font-heading text-[1.25rem] font-normal leading-[1.15] text-ink-muted lg:text-[1.375rem]">
                HealthPolicy Simulator
              </span>
            </Link>

            <div className="flex items-center gap-3">
              <form onSubmit={onLookup} className="relative hidden md:block" role="search">
                <label htmlFor="run-lookup" className="sr-only">
                  {t("nav.searchRuns")}
                </label>
                <input
                  id="run-lookup"
                  value={lookup}
                  onChange={(event) => setLookup(event.target.value)}
                  placeholder={t("nav.searchRuns")}
                  autoComplete="off"
                  className="h-10 w-64 border border-line-strong bg-surface px-3 pr-10 text-sm text-ink placeholder:text-ink-subtle focus-visible:border-accent focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
                />
                <button
                  type="submit"
                  aria-label={t("nav.searchRuns")}
                  className="absolute right-0 top-0 grid h-10 w-10 place-items-center text-ink-muted hover:text-accent"
                >
                  <Icon name="search" size={20} />
                </button>
              </form>
              <Link
                href="/runs/new"
                className="hidden h-11 items-center gap-2 rounded-md bg-accent px-5 font-heading text-base font-medium tracking-[0.02em] text-on-accent no-underline transition-colors hover:bg-accent-hover sm:inline-flex"
              >
                <Icon name="plus" size={18} />
                {t("nav.newRun")}
              </Link>
              <button
                type="button"
                onClick={() => setMobileOpen((value) => !value)}
                aria-label={t("nav.main")}
                aria-expanded={mobileOpen}
                className="grid h-11 w-11 place-items-center border border-line-strong text-ink lg:hidden"
              >
                <Icon name={mobileOpen ? "close" : "menu"} size={22} />
              </button>
            </div>
          </div>

          {mobileOpen && (
            <nav aria-label={t("nav.main")} className="mt-4 border-t border-line pt-3 lg:hidden">
              {SIDEBAR_GROUPS.map((group) => (
                <SidebarGroup key={group.titleKey} group={group} pathname={pathname} />
              ))}
              <Link
                href="/runs/new"
                className="mt-3 inline-flex h-11 items-center gap-2 rounded-md bg-accent px-5 font-heading text-base font-medium text-on-accent no-underline"
              >
                <Icon name="plus" size={18} />
                {t("nav.newRun")}
              </Link>
            </nav>
          )}
        </div>
      </header>

      {/* Primary navigation band */}
      <nav aria-label={t("nav.main")} className="border-b border-line bg-surface-muted">
        <ul className="mx-auto flex w-full max-w-content items-stretch gap-0 overflow-x-auto px-2 lg:justify-between lg:px-6">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item);
            return (
              <li key={item.href} className="shrink-0">
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "inline-flex h-[60px] items-center border-b-[3px] px-3 font-heading text-sm font-bold uppercase tracking-[0.06em] no-underline transition-colors lg:px-4 lg:text-base",
                    active
                      ? "border-accent text-accent"
                      : "border-transparent text-ink hover:text-accent",
                  )}
                >
                  {t(item.labelKey)}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Content: pale-teal section navigation + white page */}
      <div className="mx-auto flex w-full max-w-content flex-1 items-stretch">
        <aside className="hidden w-72 shrink-0 bg-surface-tint lg:block">
          <nav aria-label={t("nav.main")} className="px-6 py-6">
            {SIDEBAR_GROUPS.map((group) => (
              <SidebarGroup key={group.titleKey} group={group} pathname={pathname} />
            ))}
          </nav>
        </aside>
        <main id="main" className="min-w-0 flex-1 bg-surface px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          <ReadinessBanner />
          {children}
        </main>
      </div>

      {/* Footer */}
      <footer className="bg-footer text-white">
        <div className="mx-auto w-full max-w-content px-4 lg:px-6">
          <div className="flex justify-center border-b border-white/20 py-4">
            <a
              href="#top"
              className="inline-flex items-center gap-2 font-heading text-sm font-bold uppercase tracking-[0.08em] text-white no-underline hover:underline"
            >
              <Icon name="chevron-down" size={16} className="rotate-180" />
              {t("footer.top")}
            </a>
          </div>
          <div className="grid grid-cols-1 gap-8 py-10 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <h2 className="font-heading text-sm font-bold uppercase tracking-[0.08em] text-white">
                {t("footer.navigation")}
              </h2>
              <ul className="mt-3 space-y-1.5 text-sm">
                {[NAV_ITEMS[0], NAV_ITEMS[1], NAV_ITEMS[2]].map((item) =>
                  item === undefined ? null : (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className="text-white no-underline hover:underline"
                      >
                        {t(item.labelKey)}
                      </Link>
                    </li>
                  ),
                )}
              </ul>
            </div>
            <div>
              <h2 className="font-heading text-sm font-bold uppercase tracking-[0.08em] text-white">
                {t("footer.system")}
              </h2>
              <ul className="mt-3 space-y-1.5 text-sm">
                {[NAV_ITEMS[3], NAV_ITEMS[4], NAV_ITEMS[5]].map((item) =>
                  item === undefined ? null : (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className="text-white no-underline hover:underline"
                      >
                        {t(item.labelKey)}
                      </Link>
                    </li>
                  ),
                )}
              </ul>
            </div>
            <div>
              <h2 className="font-heading text-sm font-bold uppercase tracking-[0.08em] text-white">
                {t("footer.about")}
              </h2>
              <p className="mt-3 max-w-xs text-sm leading-relaxed text-white">
                {t("footer.aboutText")}
              </p>
            </div>
            <div className="flex flex-col items-start gap-2 lg:items-end lg:text-right">
              <BrandMark variant="inverse" className="h-16 w-16" />
              <p className="font-heading text-lg font-bold leading-tight text-white">
                HealthPolicy Simulator
              </p>
              <p className="max-w-[16rem] text-sm text-white">{t("footer.organisation")}</p>
            </div>
          </div>
          <div className="border-t border-white/20 py-4 text-2xs text-white">
            {t("footer.legal")}
          </div>
        </div>
      </footer>
    </div>
  );
}
