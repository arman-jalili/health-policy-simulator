import { z } from "zod";

import { TopicOutcomeKindSchema } from "@/features/contracts";

export const CitationSchema = z.object({
  passage_id: z.string(),
  resolved: z.boolean(),
  quote: z.string().nullable(),
  outlet: z.string().nullable(),
  published_on: z.string().nullable(),
  medium: z.string().nullable(),
  page_from: z.number().int().nullable(),
  page_to: z.number().int().nullable(),
  source_uri: z.string().nullable(),
});
export type Citation = z.infer<typeof CitationSchema>;

export const CitedStatementSchema = z.object({
  text: z.string(),
  status: z.enum(["evidenced", "narrative", "unsupported"]),
  claim_ids: z.array(z.string()).default([]),
  citations: z.array(CitationSchema).default([]),
});
export type CitedStatement = z.infer<typeof CitedStatementSchema>;

export const BriefSectionSchema = z.object({
  kind: z.string(),
  ordinal: z.number().int().min(1).max(8),
  statements: z.array(CitedStatementSchema).default([]),
});
export type BriefSection = z.infer<typeof BriefSectionSchema>;

export const RejectedProposalSchema = z.object({
  measure: z.string(),
  blocking_stakeholders: z.array(z.string()).default([]),
  reasons: z.array(z.string()).default([]),
});
export type RejectedProposal = z.infer<typeof RejectedProposalSchema>;

export const TopicOutcomeSchema = z.object({
  topic: z.string(),
  kind: TopicOutcomeKindSchema,
  blocking_stakeholders: z.array(z.string()).default([]),
  reason: z.string().nullable(),
});
export type TopicOutcome = z.infer<typeof TopicOutcomeSchema>;

export const DisclaimerSchema = z.object({
  text: z.string(),
  model_reference: z.string(),
  prompt_version: z.string(),
});

export const BriefVersionSchema = z.object({
  number: z.number().int().min(1),
  run_id: z.string(),
  snapshot_ref: z.string(),
  generated_at: z.string(),
  previous_version: z.number().int().nullable(),
  reason: z.string().nullable(),
});
export type BriefVersion = z.infer<typeof BriefVersionSchema>;

export const BriefResponseSchema = z.object({
  brief_id: z.string(),
  run_id: z.string(),
  status: z.string(),
  version: BriefVersionSchema,
  sections: z.array(BriefSectionSchema),
  rejected_proposals: z.array(RejectedProposalSchema).default([]),
  outcomes: z.array(TopicOutcomeSchema).default([]),
  disclaimer: DisclaimerSchema,
  citation_count: z.number().int().min(0),
  schema_version: z.string().optional(),
});
export type BriefResponse = z.infer<typeof BriefResponseSchema>;

export const BriefVersionSummarySchema = z.object({
  brief_id: z.string(),
  version: z.number().int().min(1),
  previous_version: z.number().int().nullable(),
  reason: z.string().nullable(),
  status: z.string(),
  generated_at: z.string(),
});
export type BriefVersionSummary = z.infer<typeof BriefVersionSummarySchema>;

export const BriefVersionListSchema = z.object({
  run_id: z.string(),
  versions: z.array(BriefVersionSummarySchema).default([]),
});
export type BriefVersionList = z.infer<typeof BriefVersionListSchema>;

export const VersionBriefBodySchema = z.object({ reason: z.string().min(1) });
export const VersionBriefResponseSchema = z.object({
  brief_id: z.string(),
  previous_version: z.number().int().min(1),
  version: z.number().int().min(2),
  reason: z.string(),
});

export const CitationListSchema = z.object({
  brief_id: z.string(),
  section: z.string().nullable(),
  items: z.array(CitationSchema).default([]),
});
export type CitationList = z.infer<typeof CitationListSchema>;

export const BRIEF_SECTION_ORDER = [
  "question_summary",
  "actors_involved",
  "negotiation_history",
  "conflict_analysis",
  "compromise_proposals",
  "consensus_analysis",
  "open_disputes",
  "impact",
] as const;

export type BriefSectionKind = (typeof BRIEF_SECTION_ORDER)[number];
