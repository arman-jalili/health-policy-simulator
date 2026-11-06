import { z } from "zod";

import {
  AttributionStrengthSchema,
  BudgetPeriodSchema,
  InstitutionCategorySchema,
  PowerSourceKindSchema,
  ProposalClassSchema,
} from "@/features/contracts";

export const InstitutionSchema = z.object({
  name: z.string(),
  short_name: z.string(),
  category: InstitutionCategorySchema,
  code: z.string(),
});
export type Institution = z.infer<typeof InstitutionSchema>;

export const StakeholderSummarySchema = z.object({
  stakeholder_id: z.string(),
  identity: InstitutionSchema,
  interest_count: z.number().int(),
  constraint_count: z.number().int(),
  profile_version: z.string(),
});
export type StakeholderSummary = z.infer<typeof StakeholderSummarySchema>;

export const StakeholdersResponseSchema = z.object({
  items: z.array(StakeholderSummarySchema),
});
export type StakeholdersResponse = z.infer<typeof StakeholdersResponseSchema>;

export const HistoricalPositionSchema = z.object({
  position_id: z.string(),
  stakeholder_id: z.string(),
  stance: z.string(),
  attribution: AttributionStrengthSchema,
  stated_on: z.string(),
  passage_id: z.string(),
  usable: z.boolean(),
});
export type HistoricalPosition = z.infer<typeof HistoricalPositionSchema>;

export const HistoricalPositionsResponseSchema = z.object({
  stakeholder_id: z.string(),
  positions: z.array(HistoricalPositionSchema),
});
export type HistoricalPositionsResponse = z.infer<typeof HistoricalPositionsResponseSchema>;

export const HistoricalPositionBodySchema = z.object({
  stance: z.string().min(1),
  attribution: AttributionStrengthSchema,
  stated_on: z.string().min(1),
  passage_id: z.string().min(1),
});
export type HistoricalPositionBody = z.infer<typeof HistoricalPositionBodySchema>;

export const MandateSourceSchema = z.object({
  kind: PowerSourceKindSchema,
  citation: z.string(),
  as_of: z.string(),
});

export const CitePowerSourceBodySchema = z.object({
  power_type: z.string().min(1),
  proposal_class: ProposalClassSchema.optional(),
  citation: z.string().min(1),
  kind: PowerSourceKindSchema,
  as_of: z.string().min(1),
});
export type CitePowerSourceBody = z.infer<typeof CitePowerSourceBodySchema>;

export const CitePowerSourceResponseSchema = z.object({
  accepted: z.boolean(),
  reason: z.string().nullable(),
});
export type CitePowerSourceResponse = z.infer<typeof CitePowerSourceResponseSchema>;

export const InterestSchema = z.object({
  topic: z.string(),
  goal: z.string(),
  weight: z.number().min(0).max(1),
});

export const ConstraintSchema = z.object({
  statement: z.string(),
  topic: z.string(),
});

export const PrioritySchema = z.object({
  rank: z.number().int().min(1),
  topic: z.string(),
});

export const VetoRightSchema = z.object({
  proposal_class: ProposalClassSchema,
  source: MandateSourceSchema,
});

export const BudgetSchema = z.object({
  amount_eur: z.union([z.string(), z.number()]),
  period: BudgetPeriodSchema,
  tolerance: z.number().min(0).max(1),
  source: MandateSourceSchema,
});

export const RegisterStakeholderBodySchema = z.object({
  identity: InstitutionSchema,
  mandate_scope: z.object({
    topics: z.array(z.string()).min(1),
    description: z.string(),
    source: MandateSourceSchema,
  }),
  budget: BudgetSchema,
  interests: z.array(InterestSchema),
  constraints: z.array(ConstraintSchema),
  priorities: z.array(PrioritySchema).default([]),
  veto_rights: z.array(VetoRightSchema).default([]),
});
export type RegisterStakeholderBody = z.infer<typeof RegisterStakeholderBodySchema>;

export const RegisterStakeholderResponseSchema = z.object({
  stakeholder_id: z.string(),
  profile_version: z.string(),
});
