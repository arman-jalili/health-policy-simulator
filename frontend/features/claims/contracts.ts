import { z } from "zod";

export const MeasureSchema = z.object({
  measure: z.string(),
  unit: z.string(),
  period: z.string(),
  geography: z.string(),
});
export type Measure = z.infer<typeof MeasureSchema>;

export const VerifyClaimBodySchema = z.object({
  text: z.string().min(1),
  claim_type: z.string().optional(),
  measure: MeasureSchema.optional(),
  asserted_value: z.string().optional(),
});
export type VerifyClaimBody = z.infer<typeof VerifyClaimBodySchema>;

export const ClaimVerdictSchema = z.object({
  claim_id: z.string(),
  verdict: z.string(),
  path: z.string(),
  claim_type: z.string(),
  sources: z.array(z.string()),
  delta: z.string().nullable(),
});
export type ClaimVerdict = z.infer<typeof ClaimVerdictSchema>;

export const ClaimDetailSchema = ClaimVerdictSchema.extend({
  text: z.string(),
  review_verdict: z.string().nullable(),
  review_basis: z.string().nullable(),
});
export type ClaimDetail = z.infer<typeof ClaimDetailSchema>;

export const FlagBodySchema = z.object({ reason: z.string().min(1) });
export const ReviewBodySchema = z.object({
  verdict: z.string().min(1),
  basis: z.string().min(1),
});

export const ReferenceFigureSchema = z.object({
  figure_id: z.string(),
  measure: z.string(),
  unit: z.string(),
  period: z.string(),
  geography: z.string(),
  value: z.string(),
  tier: z.string(),
  as_of: z.string(),
  source_id: z.string(),
});
export type ReferenceFigure = z.infer<typeof ReferenceFigureSchema>;

export const ReferenceFiguresResponseSchema = z.object({
  items: z.array(ReferenceFigureSchema),
});
export type ReferenceFiguresResponse = z.infer<typeof ReferenceFiguresResponseSchema>;

export const ReferenceFigureBodySchema = z.object({
  measure: MeasureSchema,
  value: z.string().min(1),
  tier: z.string().min(1),
  as_of: z.string().min(1),
  source_id: z.string().min(1),
});
export type ReferenceFigureBody = z.infer<typeof ReferenceFigureBodySchema>;

export const ContradictionItemSchema = z.object({
  finding_id: z.string(),
  claim_id_a: z.string(),
  claim_id_b: z.string(),
  measure: z.string(),
  delta: z.string(),
});
export type ContradictionItem = z.infer<typeof ContradictionItemSchema>;

export const ContradictionResponseSchema = z.object({
  items: z.array(ContradictionItemSchema),
});
export type ContradictionResponse = z.infer<typeof ContradictionResponseSchema>;
