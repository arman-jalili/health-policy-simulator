import { beforeEach, describe, expect, it } from "vitest";

import { enumLabel, translate } from "@/lib/i18n";
import {
  DEFAULT_SETTINGS,
  SeedSchema,
  addRunToIndex,
  clearRunIndex,
  loadRunIndex,
  loadSeed,
  loadSettings,
  saveSeed,
  saveSettings,
  updateRunInIndex,
} from "@/lib/settings";

describe("settings store", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns defaults when nothing is stored", () => {
    expect(loadSettings()).toEqual(DEFAULT_SETTINGS);
  });

  it("round-trips a saved setting set", () => {
    saveSettings({ ...DEFAULT_SETTINGS, theme: "ink", density: "compact", locale: "en" });
    const loaded = loadSettings();
    expect(loaded.theme).toBe("ink");
    expect(loaded.density).toBe("compact");
    expect(loaded.locale).toBe("en");
  });

  it("resets a corrupt settings payload instead of throwing", () => {
    window.localStorage.setItem("hps.settings.v1", "{not json");
    expect(loadSettings()).toEqual(DEFAULT_SETTINGS);
  });

  it("keeps a deduplicated, most-recent-first run index", () => {
    addRunToIndex({
      runId: "run_1",
      question: "Frage 1",
      createdAt: "2026-11-06T06:00:00Z",
      phase: "position_formation",
      round: 0,
      closed: false,
      mandateHash: "sha256:1",
    });
    addRunToIndex({
      runId: "run_2",
      question: "Frage 2",
      createdAt: "2026-11-06T06:01:00Z",
      phase: "debate",
      round: 1,
      closed: false,
      mandateHash: "sha256:2",
    });
    addRunToIndex({
      runId: "run_1",
      question: "Frage 1 neu",
      createdAt: "2026-11-06T06:02:00Z",
      phase: "closed",
      round: 1,
      closed: true,
      mandateHash: "sha256:1",
    });
    const index = loadRunIndex();
    expect(index).toHaveLength(2);
    expect(index[0]?.runId).toBe("run_1");
    expect(index[0]?.question).toBe("Frage 1 neu");
    updateRunInIndex("run_2", { closed: true, phase: "closed" });
    expect(loadRunIndex().find((item) => item.runId === "run_2")?.closed).toBe(true);
    clearRunIndex();
    expect(loadRunIndex()).toEqual([]);
  });

  it("validates and clears the demo seed", () => {
    const seed = {
      document_id: "doc_1",
      snapshot_id: "snp_1",
      figure_ids: ["fig_1"],
      pack_ids: { kassenstellen: "evp_1" },
      topics: [{ slug: "kassenstellen", claim: "Die Kassenstellen sollen ausgebaut werden." }],
    };
    expect(SeedSchema.safeParse(seed).success).toBe(true);
    saveSeed(seed);
    expect(loadSeed()).toEqual(seed);
    window.localStorage.setItem("hps.seed.v1", JSON.stringify({ document_id: "doc_1" }));
    expect(loadSeed()).toBeNull();
  });
});

describe("i18n", () => {
  it("translates German and English copy with parameters", () => {
    expect(translate("de-AT", "run.round", { round: 2, cap: 5 })).toBe("Runde 2 / 5");
    expect(translate("en", "run.round", { round: 2, cap: 5 })).toBe("Round 2 / 5");
  });

  it("localizes known enum values and falls back for unknown ones", () => {
    expect(enumLabel("stance", "conditional_accept", "de-AT")).toBe("Bedingte Zustimmung");
    expect(enumLabel("stance", "conditional_accept", "en")).toBe("Conditional acceptance");
    expect(enumLabel("stance", "future_stance", "de-AT")).toBe("Future Stance");
  });
});
