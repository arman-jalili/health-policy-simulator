import { beforeEach, describe, expect, it } from "vitest";

import {
  loadIngestionRuns,
  loadSnapshots,
  saveIngestionRun,
  saveSnapshot,
} from "@/lib/corpus-history";

describe("corpus history", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("keeps ingestion runs most-recent-first and unique per run", () => {
    saveIngestionRun({
      runId: "run_1",
      shardLabel: "shard-a",
      status: "running",
      attempted: 0,
      accepted: 0,
      quarantined: 0,
      failed: 0,
      createdAt: "2026-11-06T08:00:00Z",
    });
    saveIngestionRun({
      runId: "run_2",
      shardLabel: "shard-b",
      status: "completed",
      attempted: 2,
      accepted: 2,
      quarantined: 0,
      failed: 0,
      createdAt: "2026-11-06T08:01:00Z",
    });
    saveIngestionRun({
      runId: "run_1",
      shardLabel: "shard-a",
      status: "completed",
      attempted: 1,
      accepted: 1,
      quarantined: 0,
      failed: 0,
      createdAt: "2026-11-06T08:00:00Z",
    });

    const entries = loadIngestionRuns();
    expect(entries.map((entry) => entry.runId)).toEqual(["run_1", "run_2"]);
    expect(entries[0]?.status).toBe("completed");
  });

  it("keeps pinned snapshots unique by id", () => {
    const snapshot = {
      snapshotId: "snp_1",
      label: "pressespiegel-2020",
      manifestHash: "sha256:abc",
      pinnedAt: "2026-11-06T08:00:00Z",
      documentCount: 231,
      passageCount: 4297,
    };
    saveSnapshot(snapshot);
    saveSnapshot({ ...snapshot, passageCount: 4300 });

    const entries = loadSnapshots();
    expect(entries).toHaveLength(1);
    expect(entries[0]?.passageCount).toBe(4300);
  });

  it("ignores a corrupt history payload instead of throwing", () => {
    window.localStorage.setItem("hps.ingestion-runs.v1", "{not json");
    expect(loadIngestionRuns()).toEqual([]);
  });
});
