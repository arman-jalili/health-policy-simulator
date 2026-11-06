import { z } from "zod";

export const IngestionRunEntrySchema = z.object({
  runId: z.string().min(1),
  shardLabel: z.string(),
  status: z.string(),
  attempted: z.number().int(),
  accepted: z.number().int(),
  quarantined: z.number().int(),
  failed: z.number().int(),
  createdAt: z.string(),
});
export type IngestionRunEntry = z.infer<typeof IngestionRunEntrySchema>;

export const SnapshotEntrySchema = z.object({
  snapshotId: z.string().min(1),
  label: z.string(),
  manifestHash: z.string(),
  pinnedAt: z.string(),
  documentCount: z.number().int(),
  passageCount: z.number().int(),
});
export type SnapshotEntry = z.infer<typeof SnapshotEntrySchema>;

const INGESTION_KEY = "hps.ingestion-runs.v1";
const SNAPSHOT_KEY = "hps.corpus-snapshots.v1";
const LIMIT = 25;

function hasStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function read(key: string): string | null {
  if (!hasStorage()) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  if (!hasStorage()) return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // History is a convenience; ingestion itself does not depend on it.
  }
}

export function loadIngestionRuns(): IngestionRunEntry[] {
  const raw = read(INGESTION_KEY);
  if (raw === null) return [];
  try {
    const parsed = z.array(IngestionRunEntrySchema).safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

export function saveIngestionRun(entry: IngestionRunEntry): void {
  const others = loadIngestionRuns().filter((item) => item.runId !== entry.runId);
  write(INGESTION_KEY, JSON.stringify([entry, ...others].slice(0, LIMIT)));
}

export function loadSnapshots(): SnapshotEntry[] {
  const raw = read(SNAPSHOT_KEY);
  if (raw === null) return [];
  try {
    const parsed = z.array(SnapshotEntrySchema).safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

export function saveSnapshot(entry: SnapshotEntry): void {
  const others = loadSnapshots().filter((item) => item.snapshotId !== entry.snapshotId);
  write(SNAPSHOT_KEY, JSON.stringify([entry, ...others].slice(0, LIMIT)));
}
