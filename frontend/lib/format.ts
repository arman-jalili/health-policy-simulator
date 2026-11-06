import type { Locale } from "@/lib/i18n";

const DE_AT = "de-AT";
const EN_GB = "en-GB";

function intlLocale(locale: Locale): string {
  return locale === "en" ? EN_GB : DE_AT;
}

export interface EurOptions {
  readonly minimumFractionDigits?: number;
  readonly maximumFractionDigits?: number;
  readonly compact?: boolean;
}

export function parseDecimal(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatEur(
  value: string | number | null | undefined,
  locale: Locale,
  options: EurOptions = {},
): string {
  const parsed = parseDecimal(value);
  if (parsed === null) return "—";
  return new Intl.NumberFormat(intlLocale(locale), {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: options.minimumFractionDigits ?? 2,
    maximumFractionDigits: options.maximumFractionDigits ?? 2,
    notation: options.compact === true ? "compact" : "standard",
  }).format(parsed);
}

export function formatEurExact(
  value: string | number | null | undefined,
  locale: Locale,
): string {
  return formatEur(value, locale, { minimumFractionDigits: 6, maximumFractionDigits: 6 });
}

export function formatNumber(
  value: number | null | undefined,
  locale: Locale,
  maximumFractionDigits = 0,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat(intlLocale(locale), { maximumFractionDigits }).format(value);
}

export function formatDecimal(value: string | null | undefined, locale: Locale): string {
  const parsed = parseDecimal(value);
  if (parsed === null) return "—";
  return new Intl.NumberFormat(intlLocale(locale), {
    maximumFractionDigits: 6,
  }).format(parsed);
}

export function formatPercent(
  fraction: number | null | undefined,
  locale: Locale,
  maximumFractionDigits = 0,
): string {
  if (fraction === null || fraction === undefined || !Number.isFinite(fraction)) return "—";
  return new Intl.NumberFormat(intlLocale(locale), {
    style: "percent",
    maximumFractionDigits,
  }).format(fraction);
}

const TIME_ZONE = "Europe/Vienna";

export function formatDate(iso: string | null | undefined, locale: Locale): string {
  if (iso === null || iso === undefined || iso === "") return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(intlLocale(locale), {
    timeZone: TIME_ZONE,
    dateStyle: "medium",
  }).format(date);
}

export function formatDateTime(iso: string | null | undefined, locale: Locale): string {
  if (iso === null || iso === undefined || iso === "") return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(intlLocale(locale), {
    timeZone: TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatTime(iso: string | null | undefined, locale: Locale): string {
  if (iso === null || iso === undefined || iso === "") return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(intlLocale(locale), {
    timeZone: TIME_ZONE,
    timeStyle: "medium",
  }).format(date);
}

export function formatRelative(
  iso: string | null | undefined,
  locale: Locale,
  now: number = Date.now(),
): string {
  if (iso === null || iso === undefined || iso === "") return "—";
  const timestamp = new Date(iso).getTime();
  if (Number.isNaN(timestamp)) return "—";
  const deltaSeconds = Math.round((timestamp - now) / 1000);
  const formatter = new Intl.RelativeTimeFormat(intlLocale(locale), { numeric: "auto" });
  const absolute = Math.abs(deltaSeconds);
  if (absolute < 60) return formatter.format(deltaSeconds, "second");
  const minutes = Math.round(deltaSeconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

export function truncateMiddle(value: string, head = 10, tail = 6): string {
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

export function dash(value: string | null | undefined): string {
  return value === null || value === undefined || value === "" ? "—" : value;
}

export function toNumberList(values: readonly string[]): number[] {
  return values
    .map((value) => parseDecimal(value))
    .filter((value): value is number => value !== null);
}
