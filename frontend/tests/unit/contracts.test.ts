import { describe, expect, it } from "vitest";

import { BriefResponseSchema } from "@/features/brief/contracts";
import { ClaimDetailSchema, ClaimVerdictSchema, ContradictionResponseSchema, ReferenceFiguresResponseSchema } from "@/features/claims/contracts";
import { ConsensusResponseSchema } from "@/features/consensus/contracts";
import { PassageSchema, SnapshotSchema } from "@/features/corpus/contracts";
import { EvidencePackSchema } from "@/features/evidence/contracts";
import { AllowlistSchema, GuardCheckResponseSchema, ViolationListSchema } from "@/features/governance/contracts";
import { ReadyzSchema } from "@/features/platform/contracts";
import {
  ArgumentResponseSchema,
  CloseRoundResponseSchema,
  EventsResponseSchema,
  JobResponseSchema,
  OpenRunResponseSchema,
  PositionResponseSchema,
  RunResponseSchema,
  UsageResponseSchema,
} from "@/features/run/contracts";
import {
  HistoricalPositionsResponseSchema,
  StakeholdersResponseSchema,
} from "@/features/stakeholders/contracts";

const runState = {
  run_id: "run_01M6Q0000000000000000000",
  phase: "position_formation",
  round: 1,
  round_cap: 2,
  closed: false,
  bound_stakeholder_ids: ["stk_aerztekammer"],
  open_position_ids: ["pos_01M6Q0000000000000000000"],
  coalition_ids: [],
};

const provenance = {
  outlet: "Der Standard",
  published_on: "2020-03-14",
  medium: "print",
  page_from: 7,
  page_to: 7,
  offsets: { start: 1420, end: 1985 },
  source_uri: "file:///corpus/issue-142.pdf",
};

describe("run contracts", () => {
  it("accepts an open-run response", () => {
    const parsed = OpenRunResponseSchema.safeParse({
      run_id: runState.run_id,
      phase: "position_formation",
      mandate_hash: "sha256:9fb7",
      bound: [
        {
          stakeholder_id: "stk_aerztekammer",
          institution_name: "Österreichische Ärztekammer",
          institution_code: "aerztekammer",
          profile_version: "2026.1",
          persona_version: "2026.1",
        },
      ],
    });
    expect(parsed.success).toBe(true);
  });

  it("accepts run state and events", () => {
    expect(RunResponseSchema.safeParse(runState).success).toBe(true);
    const parsed = EventsResponseSchema.safeParse({
      items: [
        {
          sequence: 1,
          event_type: "SimulationRunOpened",
          payload: { run_id: runState.run_id, snapshot_id: "snp_1" },
          occurred_at: "2026-11-06T06:23:11.412Z",
        },
      ],
      state: runState,
    });
    expect(parsed.success).toBe(true);
  });

  it("accepts positions, arguments and close-round responses", () => {
    expect(
      PositionResponseSchema.safeParse({
        position_id: "pos_1",
        run_id: runState.run_id,
        round: 1,
        stakeholder_id: "stk_aerztekammer",
        topic: "Kassenstellen",
        stance: "support",
        proposal: { summary: "Ausbau", components: [] },
        evidence_ids: ["evp_1"],
        supersedes: null,
        revision: null,
      }).success,
    ).toBe(true);
    expect(
      ArgumentResponseSchema.safeParse({
        argument_id: "arg_1",
        run_id: runState.run_id,
        round: 1,
        stakeholder_id: "stk_aerztekammer",
        target: { topic: "Kassenstellen", position_id: null, argument_id: null },
        stance: "support",
        evidence_ids: ["evp_1"],
        unsupported: false,
        invocation_id: "inv_demo_1",
      }).success,
    ).toBe(true);
    expect(
      CloseRoundResponseSchema.safeParse({
        run_id: runState.run_id,
        round: 1,
        learning: { learning_id: "lrn_1", run_id: runState.run_id, round: 1, insights: [] },
        stopping_condition: { name: "round_cap", fired: true, parameters: {} },
      }).success,
    ).toBe(true);
  });

  it("accepts usage and job responses", () => {
    expect(
      UsageResponseSchema.safeParse({
        run_id: runState.run_id,
        total_invocations: 9,
        input_tokens: 1107,
        output_tokens: 405,
        cost: "1.161000",
        by_stakeholder: [
          {
            stakeholder: "stk_aerztekammer",
            invocations: 1,
            input_tokens: 123,
            output_tokens: 45,
            cost: "0.129",
          },
        ],
        by_round: [
          { round: 0, invocations: 9, input_tokens: 1107, output_tokens: 405, cost: "1.161000" },
        ],
      }).success,
    ).toBe(true);
    expect(
      JobResponseSchema.safeParse({
        job_id: "job_1",
        run_id: runState.run_id,
        status: "running",
        attempts: 1,
        checkpoint: {
          run_id: runState.run_id,
          round: 1,
          phase: "rounds",
          next_actor: "stk_oegk",
          budget_used_invocations: 3,
          budget_used_tokens: 400,
          budget_used_cost: "0.020000",
        },
        error: null,
        progress_sequence: 12,
      }).success,
    ).toBe(true);
  });
});

describe("consensus, brief and evidence contracts", () => {
  it("accepts a consensus response", () => {
    const parsed = ConsensusResponseSchema.safeParse({
      records: [
        {
          consensus_id: "cns_1",
          run_id: runState.run_id,
          topic: "cost_control",
          proposal_class: "other",
          outcome: "consensus",
          support: 1,
          threshold: 0.5,
          supporters: ["stk_aerztekammer"],
          minorities: [{ holders: ["stk_oegk"], objections: ["Finanzierung unklar"] }],
          blockers: [],
          reason: null,
        },
      ],
    });
    expect(parsed.success).toBe(true);
  });

  it("accepts an eight-section brief", () => {
    const parsed = BriefResponseSchema.safeParse({
      brief_id: "brf_1",
      run_id: runState.run_id,
      status: "published",
      version: {
        number: 1,
        run_id: runState.run_id,
        snapshot_ref: "mandate:9fb7",
        generated_at: "2026-11-06T06:30:00Z",
        previous_version: null,
        reason: null,
      },
      sections: [
        {
          kind: "question_summary",
          ordinal: 1,
          statements: [
            {
              text: "Wie sichern wir Kassenstellen?",
              status: "narrative",
              claim_ids: [],
              citations: [],
            },
          ],
        },
      ],
      rejected_proposals: [],
      outcomes: [
        { topic: "Kassenstellen", kind: "recommendation", blocking_stakeholders: [], reason: null },
      ],
      disclaimer: {
        text: "Simulation, keine Entscheidung.",
        model_reference: "scripted-local",
        prompt_version: "brief@1",
      },
      citation_count: 0,
      schema_version: "1.0",
    });
    expect(parsed.success).toBe(true);
  });

  it("accepts an evidence pack with absence and score decomposition", () => {
    const parsed = EvidencePackSchema.safeParse({
      pack_id: "evp_1",
      claim: "Die Kassenstellen sollen ausgebaut werden.",
      snapshot_id: "snp_1",
      index_version: "v1",
      candidates: [
        {
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
          provenance,
        },
      ],
      absence: null,
      trace: {
        embedding_model: "hashing-char3gram-v1",
        reranker_model: "none",
        query_rewrite: "Kassenstellen",
        stance_counts: { supporting: 1 },
        retrieval_mode: "lexical+dense",
        index_version: "v1",
      },
      frozen_at: "2026-11-06T06:25:00Z",
    });
    expect(parsed.success).toBe(true);
  });
});

describe("governance, stakeholders, claims, corpus and platform contracts", () => {
  it("accepts guard and allowlist responses", () => {
    expect(
      GuardCheckResponseSchema.safeParse({
        decision: "rewrite",
        violations: [
          {
            violation_id: "vio_1",
            violation_class: "person_named",
            offending_span: "Dr. Kurz",
            rewritten_span: "[person]",
            rule_id: "GC-001",
            rule_version: "1",
            detected_at: "2026-11-06T06:20:00Z",
          },
        ],
        rewritten_text: "[person] sagte",
        rule_version: "GC-001+GC-002+GC-003+GC-004+GC-005",
      }).success,
    ).toBe(true);
    expect(ViolationListSchema.safeParse({ items: [] }).success).toBe(true);
    expect(
      AllowlistSchema.safeParse({
        institutions: [
          {
            code: "aerztekammer",
            canonical_name: "Österreichische Ärztekammer",
            short_name: "Ärztekammer",
            category: "professional_body",
            aliases: ["Ärztekammer"],
          },
        ],
        version: "2026.1",
      }).success,
    ).toBe(true);
  });

  it("accepts stakeholder summaries and history", () => {
    expect(
      StakeholdersResponseSchema.safeParse({
        items: [
          {
            stakeholder_id: "stk_aerztekammer",
            identity: {
              name: "Österreichische Ärztekammer",
              short_name: "Ärztekammer",
              category: "professional_body",
              code: "aerztekammer",
            },
            interest_count: 2,
            constraint_count: 2,
            profile_version: "2026.1",
          },
        ],
      }).success,
    ).toBe(true);
    expect(
      HistoricalPositionsResponseSchema.safeParse({
        stakeholder_id: "stk_aerztekammer",
        positions: [
          {
            position_id: "pos_1",
            stakeholder_id: "stk_aerztekammer",
            stance: "oppose",
            attribution: "explicit",
            stated_on: "2020-03-14",
            passage_id: "psg_1",
            usable: true,
          },
        ],
      }).success,
    ).toBe(true);
  });

  it("accepts claim verdicts and reference figures", () => {
    expect(
      ClaimVerdictSchema.safeParse({
        claim_id: "clm_1",
        verdict: "verified",
        path: "reference_comparison",
        claim_type: "quantitative",
        sources: ["fig_1"],
        delta: "0.4",
      }).success,
    ).toBe(true);
    expect(
      ClaimDetailSchema.safeParse({
        claim_id: "clm_1",
        verdict: "ambiguous",
        path: "reference_comparison",
        claim_type: "quantitative",
        sources: [],
        delta: null,
        text: "Wartezeiten stiegen um 22 %",
        review_verdict: null,
        review_basis: null,
      }).success,
    ).toBe(true);
    expect(ContradictionResponseSchema.safeParse({ items: [] }).success).toBe(true);
    expect(
      ReferenceFiguresResponseSchema.safeParse({
        items: [
          {
            figure_id: "fig_1",
            measure: "public_health_spend",
            unit: "EUR",
            period: "2019",
            geography: "AT",
            value: "42100000000",
            tier: "official_statistics",
            as_of: "2020-12-31",
            source_id: "statistik-austria",
          },
        ],
      }).success,
    ).toBe(true);
  });

  it("accepts a passage, snapshot and readiness body", () => {
    expect(
      PassageSchema.safeParse({
        passage_id: "psg_1",
        text: "Die Wartezeiten stiegen um 22 Prozent.",
        provenance,
        speaker_kind: "institution",
        citable: true,
      }).success,
    ).toBe(true);
    expect(
      SnapshotSchema.safeParse({
        snapshot_id: "snp_1",
        label: "demo-corpus-v1",
        manifest_hash: "sha256:abc",
        pinned_at: "2026-11-06T06:20:00Z",
        document_ids: ["doc_1"],
        index: {
          index_version: "v1",
          embedding_model: "hashing-char3gram-v1",
          searchable_since: "2026-11-06T06:20:00Z",
          passage_count: 12,
        },
      }).success,
    ).toBe(true);
    expect(
      ReadyzSchema.safeParse({
        status: "ready",
        service: "health-policy-simulator",
        checks: { database: "ok", llm: "scripted", attribution: "client-declared" },
      }).success,
    ).toBe(true);
  });

  it("rejects a malformed run state", () => {
    const parsed = RunResponseSchema.safeParse({ run_id: "run_1", phase: "unknown" });
    expect(parsed.success).toBe(false);
  });
});
