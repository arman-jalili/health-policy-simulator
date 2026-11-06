import { z } from "zod";

import {
  BasisKindSchema,
  ConsensusOutcomeSchema,
  DerivationInputKindSchema,
  FeasibilityLevelSchema,
  PackageStateSchema,
  ProposalClassSchema,
  StanceSchema,
  UncertaintyLabelSchema,
} from "@/features/contracts";

export const MinoritySchema = z.object({
  holders: z.array(z.string()),
  objections: z.array(z.string()),
});
export type Minority = z.infer<typeof MinoritySchema>;

export const ConsensusRecordSchema = z.object({
  consensus_id: z.string(),
  run_id: z.string(),
  topic: z.string(),
  proposal_class: ProposalClassSchema,
  outcome: ConsensusOutcomeSchema,
  support: z.number().min(0).max(1),
  threshold: z.number().gt(0).max(1),
  supporters: z.array(z.string()),
  minorities: z.array(MinoritySchema),
  blockers: z.array(z.string()),
  reason: z.string().nullable(),
});
export type ConsensusRecord = z.infer<typeof ConsensusRecordSchema>;

export const ConsensusResponseSchema = z.object({ records: z.array(ConsensusRecordSchema) });
export type ConsensusResponse = z.infer<typeof ConsensusResponseSchema>;

export const DeriveBodySchema = z.object({ topics: z.array(z.string()).default([]) });

export const StancePositionSchema = z.object({
  stakeholder: z.string(),
  stance: StanceSchema,
  weight: z.number().min(0).max(1),
  recorded: z.boolean(),
  log_position: z.number().int().nullable(),
});
export type StancePosition = z.infer<typeof StancePositionSchema>;

export const UnresolvedConflictSchema = z.object({
  topic: z.string(),
  positions: z.array(StancePositionSchema),
});
export type UnresolvedConflict = z.infer<typeof UnresolvedConflictSchema>;

export const UnresolvedConflictListSchema = z.object({
  conflicts: z.array(UnresolvedConflictSchema),
});

export const ComposePackageBodySchema = z.object({
  component_ids: z.array(z.string()).default([]),
  rejected_ids: z.array(z.string()).default([]),
});
export type ComposePackageBody = z.infer<typeof ComposePackageBodySchema>;

export const ComposePackageResponseSchema = z.object({
  package_id: z.string(),
  component_ids: z.array(z.string()),
  rejected_count: z.number().int().min(0),
  state: PackageStateSchema,
});
export type ComposePackageResponse = z.infer<typeof ComposePackageResponseSchema>;

export const PackageSummarySchema = z.object({
  package_id: z.string(),
  state: PackageStateSchema,
  component_count: z.number().int().min(0),
  rejected_count: z.number().int().min(0),
});
export type PackageSummary = z.infer<typeof PackageSummarySchema>;

export const PackageListSchema = z.object({ packages: z.array(PackageSummarySchema) });
export type PackageList = z.infer<typeof PackageListSchema>;

export const DerivationInputSchema = z.object({
  kind: DerivationInputKindSchema,
  reference_id: z.string().min(1).max(200),
  description: z.string().default(""),
});
export type DerivationInput = z.infer<typeof DerivationInputSchema>;

export const EstimateBasisSchema = z.object({
  kind: BasisKindSchema,
  inputs: z.array(DerivationInputSchema).default([]),
});
export type EstimateBasis = z.infer<typeof EstimateBasisSchema>;

export const EstimateLimitationSchema = z.object({
  statement: z.string(),
  ignored_factors: z.array(z.string()).default([]),
});

export const EstimatedFigureSchema = z.object({
  field: z.string(),
  value: z.string(),
  basis: EstimateBasisSchema,
  label: UncertaintyLabelSchema,
  limitation: EstimateLimitationSchema.nullish(),
});
export type EstimatedFigure = z.infer<typeof EstimatedFigureSchema>;

export const FeasibilityRatingSchema = z.object({
  political: FeasibilityLevelSchema,
  legal: FeasibilityLevelSchema,
  administrative: FeasibilityLevelSchema,
  basis: EstimateBasisSchema,
  blockers: z.array(z.string()).default([]),
});
export type FeasibilityRating = z.infer<typeof FeasibilityRatingSchema>;

export const AssessImpactBodySchema = z.object({
  baseline: z.object({
    label: z.string().min(1).max(200),
    reference: z.string().default(""),
  }),
  horizon: z.object({
    years: z.number().int().min(1).max(50),
    description: z.string().default(""),
  }),
  assumptions: z
    .array(
      z.object({
        statement: z.string().min(1).max(1000),
        basis: EstimateBasisSchema,
      }),
    )
    .default([]),
});
export type AssessImpactBody = z.infer<typeof AssessImpactBodySchema>;

export const AssessImpactResponseSchema = z.object({
  scenario_id: z.string(),
  package_id: z.string(),
  figures: z.array(EstimatedFigureSchema),
  feasibility: FeasibilityRatingSchema.nullish(),
});
export type AssessImpactResponse = z.infer<typeof AssessImpactResponseSchema>;

export const ComparisonEntrySchema = z.object({
  package_id: z.string(),
  scenario_id: z.string(),
  cost: z.string().nullable(),
  acceptance: z.number().min(0).max(1),
  feasibility: FeasibilityRatingSchema,
  rank: z.number().int().min(1),
});
export type ComparisonEntry = z.infer<typeof ComparisonEntrySchema>;

export const ComparisonResponseSchema = z.object({
  entries: z.array(ComparisonEntrySchema),
});
export type ComparisonResponse = z.infer<typeof ComparisonResponseSchema>;
