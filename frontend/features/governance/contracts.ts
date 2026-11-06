import { z } from "zod";

import { GuardDecisionSchema, SpeakerKindSchema } from "@/features/contracts";

export const ViolationSchema = z.object({
  violation_id: z.string(),
  violation_class: z.string(),
  offending_span: z.string(),
  rewritten_span: z.string().nullable(),
  rule_id: z.string(),
  rule_version: z.string(),
  detected_at: z.string(),
});
export type Violation = z.infer<typeof ViolationSchema>;

export const ViolationListSchema = z.object({ items: z.array(ViolationSchema) });
export type ViolationList = z.infer<typeof ViolationListSchema>;

export const AllowlistItemSchema = z.object({
  code: z.string(),
  canonical_name: z.string(),
  short_name: z.string(),
  category: z.string(),
  aliases: z.array(z.string()),
});
export type AllowlistItem = z.infer<typeof AllowlistItemSchema>;

export const AllowlistSchema = z.object({
  institutions: z.array(AllowlistItemSchema),
  version: z.string(),
});
export type Allowlist = z.infer<typeof AllowlistSchema>;

export const GuardCheckBodySchema = z.object({
  text: z.string().min(1),
  speaker_kind: SpeakerKindSchema,
  invocation_id: z.string().min(1),
  run_id: z.string().nullish(),
  position_id: z.string().nullish(),
  cited_passage_ids: z.array(z.string()).default([]),
  reference_figure_ids: z.array(z.string()).default([]),
});
export type GuardCheckBody = z.infer<typeof GuardCheckBodySchema>;

export const GuardCheckResponseSchema = z.object({
  decision: GuardDecisionSchema,
  violations: z.array(ViolationSchema),
  rewritten_text: z.string().nullable(),
  rule_version: z.string(),
});
export type GuardCheckResponse = z.infer<typeof GuardCheckResponseSchema>;

export const ProvenanceSchema = z.object({
  position_id: z.string(),
  evidence_ids: z.array(z.string()),
  argument_ids: z.array(z.string()),
  invocation_id: z.string(),
  prompt_version: z.string(),
  model: z.string(),
  disclosed_at: z.string(),
  version: z.number().int(),
});
export type Provenance = z.infer<typeof ProvenanceSchema>;

export const DiscloseProvenanceBodySchema = z.object({
  version: z.number().int().nullish(),
  requested_by: z.string().nullish(),
});
export type DiscloseProvenanceBody = z.infer<typeof DiscloseProvenanceBodySchema>;
