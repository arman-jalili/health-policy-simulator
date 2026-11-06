import { z } from "zod";

export const LOCALES = ["de-AT", "en"] as const;
export const THEMES = ["paper", "ink", "dark", "system"] as const;
export const DENSITIES = ["comfortable", "compact"] as const;
export const MOTIONS = ["full", "reduced"] as const;
export const NUMBER_LOCALES = ["de-AT", "en-GB"] as const;

export const SettingsSchema = z.object({
  version: z.literal(1),
  roundCap: z.number().int().min(1).max(50),
  consensusThreshold: z.number().gt(0).max(1),
  defaultStakeholderIds: z.array(z.string()),
  defaultQuestion: z.string().min(1).max(4000),
  budgetMaxInvocations: z.number().int().min(1).max(10_000),
  locale: z.enum(LOCALES),
  theme: z.enum(THEMES),
  density: z.enum(DENSITIES),
  motion: z.enum(MOTIONS),
  timeZone: z.literal("Europe/Vienna"),
  numberLocale: z.enum(NUMBER_LOCALES),
});

export type Settings = z.infer<typeof SettingsSchema>;
export type Theme = Settings["theme"];
export type Density = Settings["density"];
export type Motion = Settings["motion"];

export const DEFAULT_QUESTION =
  "Wie können die Wartezeiten auf Facharzttermine innerhalb von fünf Jahren um 20 % gesenkt werden, ohne die Gesundheitsausgaben um mehr als 5 % zu erhöhen?";

export const DEFAULT_SETTINGS: Settings = {
  version: 1,
  roundCap: 2,
  consensusThreshold: 0.5,
  defaultStakeholderIds: [],
  defaultQuestion: DEFAULT_QUESTION,
  budgetMaxInvocations: 30,
  locale: "de-AT",
  theme: "paper",
  density: "comfortable",
  motion: "full",
  timeZone: "Europe/Vienna",
  numberLocale: "de-AT",
};

export const SeedSchema = z.object({
  document_id: z.string().min(1),
  snapshot_id: z.string().min(1),
  figure_ids: z.array(z.string()).default([]),
  pack_ids: z.record(z.string(), z.string()),
  topics: z
    .array(
      z
        .object({
          slug: z.string(),
          claim: z.string(),
        })
        .catchall(z.unknown()),
    )
    .default([]),
});

export type DemoSeed = z.infer<typeof SeedSchema>;

export const RunIndexEntrySchema = z.object({
  runId: z.string().min(1),
  question: z.string(),
  createdAt: z.string(),
  phase: z.string().nullable(),
  round: z.number().nullable(),
  closed: z.boolean().nullable(),
  mandateHash: z.string().nullish(),
  driver: z.enum(["manual", "automated"]).optional(),
});

export type RunIndexEntry = z.infer<typeof RunIndexEntrySchema>;

export const RunIndexSchema = z.array(RunIndexEntrySchema);

const SETTINGS_KEY = "hps.settings.v1";
const SEED_KEY = "hps.seed.v1";
const RUNS_KEY = "hps.runs.v1";
const RUN_LIMIT = 50;

function hasStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function readRaw(key: string): string | null {
  if (!hasStorage()) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeRaw(key: string, value: string): void {
  if (!hasStorage()) return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage may be unavailable or full; the UI remains usable without persistence.
  }
}

function removeRaw(key: string): void {
  if (!hasStorage()) return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // ignore
  }
}

export function loadSettings(): Settings {
  const raw = readRaw(SETTINGS_KEY);
  if (raw === null) return DEFAULT_SETTINGS;
  try {
    const parsed = SettingsSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : DEFAULT_SETTINGS;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: Settings): void {
  writeRaw(SETTINGS_KEY, JSON.stringify(settings));
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("hps:settings", { detail: settings }));
  }
}

export function clearSettings(): void {
  removeRaw(SETTINGS_KEY);
}

export function loadSeed(): DemoSeed | null {
  const raw = readRaw(SEED_KEY);
  if (raw === null) return null;
  try {
    const parsed = SeedSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}

export function saveSeed(seed: DemoSeed): void {
  writeRaw(SEED_KEY, JSON.stringify(seed));
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("hps:seed", { detail: seed }));
  }
}

export function clearSeed(): void {
  removeRaw(SEED_KEY);
}

export function loadRunIndex(): RunIndexEntry[] {
  const raw = readRaw(RUNS_KEY);
  if (raw === null) return [];
  try {
    const parsed = RunIndexSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

export function saveRunIndex(entries: readonly RunIndexEntry[]): void {
  writeRaw(RUNS_KEY, JSON.stringify(entries.slice(0, RUN_LIMIT)));
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("hps:runs"));
  }
}

export function addRunToIndex(entry: RunIndexEntry): void {
  const existing = loadRunIndex().filter((item) => item.runId !== entry.runId);
  saveRunIndex([entry, ...existing]);
}

export function updateRunInIndex(
  runId: string,
  patch: Partial<Omit<RunIndexEntry, "runId">>,
): void {
  const entries = loadRunIndex();
  const index = entries.findIndex((item) => item.runId === runId);
  if (index === -1) return;
  const current = entries[index];
  if (current === undefined) return;
  const updated: RunIndexEntry = { ...current, ...patch };
  entries[index] = updated;
  saveRunIndex(entries);
}

export function clearRunIndex(): void {
  removeRaw(RUNS_KEY);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("hps:runs"));
  }
}
