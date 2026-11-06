export interface ChartPalette {
  readonly surface: string;
  readonly ink: string;
  readonly muted: string;
  readonly line: string;
  readonly accent: string;
  readonly ok: string;
  readonly warn: string;
  readonly danger: string;
  readonly veto: string;
  readonly info: string;
}

const FALLBACK: ChartPalette = {
  surface: "#ffffff",
  ink: "#1f2426",
  muted: "#5a6567",
  line: "#d9d7cf",
  accent: "#a81e2e",
  ok: "#1d6b4f",
  warn: "#8a5a00",
  danger: "#a81e2e",
  veto: "#6e141f",
  info: "#1a5f8a",
};

export function readChartPalette(): ChartPalette {
  if (typeof window === "undefined") return FALLBACK;
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string): string => {
    const value = style.getPropertyValue(name).trim();
    return value === "" ? fallback : value;
  };
  return {
    surface: read("--surface", FALLBACK.surface),
    ink: read("--ink", FALLBACK.ink),
    muted: read("--ink-muted", FALLBACK.muted),
    line: read("--line", FALLBACK.line),
    accent: read("--accent", FALLBACK.accent),
    ok: read("--ok", FALLBACK.ok),
    warn: read("--warn", FALLBACK.warn),
    danger: read("--danger", FALLBACK.danger),
    veto: read("--veto", FALLBACK.veto),
    info: read("--info", FALLBACK.info),
  };
}

export type StanceToken =
  | "support"
  | "oppose"
  | "qualify"
  | "conditional_accept"
  | "abstain"
  | string;

export function stanceSymbol(stance: StanceToken): string {
  switch (stance) {
    case "support":
      return "▲";
    case "oppose":
      return "▼";
    case "qualify":
      return "◆";
    case "conditional_accept":
      return "◇";
    case "abstain":
      return "○";
    default:
      return "•";
  }
}

export function stanceColor(stance: StanceToken, palette: ChartPalette): string {
  switch (stance) {
    case "support":
      return palette.ok;
    case "oppose":
      return palette.danger;
    case "qualify":
      return palette.warn;
    case "conditional_accept":
      return palette.info;
    case "abstain":
      return palette.muted;
    default:
      return palette.muted;
  }
}

export function outcomeTone(outcome: string): "ok" | "warn" | "danger" | "veto" | "info" | "neutral" {
  switch (outcome) {
    case "consensus":
      return "ok";
    case "partial":
      return "warn";
    case "veto_blocked":
      return "veto";
    case "unresolved":
      return "danger";
    default:
      return "neutral";
  }
}

export function clamp01(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

export function niceMax(values: readonly number[], fallback = 1): number {
  const positive = values.filter((value) => Number.isFinite(value) && value > 0);
  if (positive.length === 0) return fallback;
  const max = Math.max(...positive);
  const magnitude = 10 ** Math.floor(Math.log10(max));
  return Math.ceil(max / magnitude) * magnitude;
}
