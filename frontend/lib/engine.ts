/**
 * The UI names the engine, never the model id: "Live-LLM" or "Skript (Platzhalter)".
 *
 * Model ids (`deepseek-flash`, `scripted-local`) are an implementation detail that changes with the
 * provider; the jury only needs to know whether a real model wrote the turn or a deterministic
 * stand-in did.
 */
export type EngineKind = "live" | "scripted" | "unknown";

export function engineKind(value: string | null | undefined): EngineKind {
  if (value === null || value === undefined || value === "") return "unknown";
  const normalized = value.trim().toLowerCase();
  if (normalized.startsWith("scripted") || normalized === "scripted") return "scripted";
  return "live";
}

export interface EngineLabel {
  readonly deutsche: string;
  readonly english: string;
}

const LABELS: Record<Exclude<EngineKind, "unknown">, EngineLabel> = {
  live: { deutsche: "Live-LLM", english: "Live LLM" },
  scripted: { deutsche: "Skript (Platzhalter)", english: "Scripted (placeholder)" },
};

export function engineLabel(value: string | null | undefined, locale: string): string {
  const kind = engineKind(value);
  if (kind === "unknown") return "";
  return locale === "en" ? LABELS[kind].english : LABELS[kind].deutsche;
}
