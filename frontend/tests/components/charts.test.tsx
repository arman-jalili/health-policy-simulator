import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Providers } from "@/components/providers";
import { SupportThresholdChart } from "@/features/consensus/components/support-threshold-chart";
import type { ConsensusRecord } from "@/features/consensus/contracts";
import { ScoreDecompositionChart } from "@/features/evidence/components/score-decomposition-chart";
import type { Candidate } from "@/features/evidence/contracts";

const record: ConsensusRecord = {
  consensus_id: "cns_1",
  run_id: "run_1",
  topic: "Kassenstellen",
  proposal_class: "other",
  outcome: "consensus",
  support: 1,
  threshold: 0.5,
  supporters: ["stk_aerztekammer"],
  minorities: [],
  blockers: [],
  reason: null,
};

const candidate: Candidate = {
  passage_id: "psg_1",
  stance: "supporting",
  score: {
    authority: 0.4,
    lexical: 0.8,
    semantic: 0.6,
    recency: 0.2,
    directness: 1,
    final: 0.61,
  },
  provenance: {
    outlet: "Der Standard",
    published_on: "2020-03-14",
    medium: "print",
    page_from: 7,
    page_to: 7,
    offsets: { start: 1, end: 20 },
    source_uri: "file:///corpus.pdf",
  },
};

describe("charts", () => {
  it("renders the support-vs-threshold bullet with a data table", () => {
    render(
      <Providers>
        <SupportThresholdChart records={[record]} />
      </Providers>,
    );
    expect(screen.getByRole("img", { name: "Konsensaufzeichnungen" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getAllByText("Kassenstellen").length).toBeGreaterThan(0);
  });

  it("renders the score decomposition with all score columns", () => {
    render(
      <Providers>
        <ScoreDecompositionChart candidates={[candidate]} locale="de-AT" />
      </Providers>,
    );
    expect(screen.getByRole("img", { name: "Bewertung" })).toBeInTheDocument();
    expect(screen.getAllByText("Lexikalisch").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Direktheit").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0,61").length).toBeGreaterThan(0);
  });
});
