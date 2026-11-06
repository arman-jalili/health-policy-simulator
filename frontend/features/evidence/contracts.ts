import { z } from "zod";

import { ClaimTypeSchema, SourceTypeSchema, StanceLabelSchema } from "@/features/contracts";
import { ProvenanceSchema } from "@/features/corpus/contracts";

export const ScoreSchema = z.object({
  authority: z.number(),
  lexical: z.number(),
  semantic: z.number(),
  recency: z.number(),
  directness: z.number(),
  final: z.number(),
});
export type Score = z.infer<typeof ScoreSchema>;

export const CandidateSchema = z.object({
  passage_id: z.string(),
  stance: StanceLabelSchema,
  score: ScoreSchema,
  provenance: ProvenanceSchema.nullable(),
});
export type Candidate = z.infer<typeof CandidateSchema>;

export const AbsenceSchema = z.object({
  queries: z.array(z.string()),
  snapshot_id: z.string(),
  reason: z.string(),
});
export type Absence = z.infer<typeof AbsenceSchema>;

export const TraceSchema = z.object({
  embedding_model: z.string(),
  reranker_model: z.string(),
  query_rewrite: z.string(),
  stance_counts: z.record(z.string(), z.number().int()),
  retrieval_mode: z.string(),
  index_version: z.string(),
});
export type Trace = z.infer<typeof TraceSchema>;

export const EvidencePackSchema = z.object({
  pack_id: z.string(),
  claim: z.string(),
  snapshot_id: z.string(),
  index_version: z.string(),
  candidates: z.array(CandidateSchema),
  absence: AbsenceSchema.nullable(),
  trace: TraceSchema,
  frozen_at: z.string(),
});
export type EvidencePack = z.infer<typeof EvidencePackSchema>;

export const ScoreBreakdownSchema = z.object({
  pack_id: z.string(),
  candidates: z.array(
    z.object({
      passage_id: z.string(),
      score: ScoreSchema,
    }),
  ),
});
export type ScoreBreakdown = z.infer<typeof ScoreBreakdownSchema>;

export const SearchCandidatesBodySchema = z.object({
  claim: z.string().min(1),
  claim_type: ClaimTypeSchema,
  snapshot_id: z.string().min(1),
  limit: z.number().int().min(1).max(100).default(20),
});
export type SearchCandidatesBody = z.infer<typeof SearchCandidatesBodySchema>;

export const SearchCandidatesResponseSchema = z.object({
  candidates: z.array(CandidateSchema),
});

export const AssemblePackBodySchema = z.object({
  claim: z.string().min(1),
  claim_type: ClaimTypeSchema,
  snapshot_id: z.string().min(1),
});
export type AssemblePackBody = z.infer<typeof AssemblePackBodySchema>;

export const RecencyPolicySchema = z.object({
  half_life_days: z.number().gt(0).default(540),
  exempt_source_types: z.array(SourceTypeSchema).default([]),
});

export const ReweightPackBodySchema = z.object({
  policy: RecencyPolicySchema,
});
export type ReweightPackBody = z.infer<typeof ReweightPackBodySchema>;
