import { z } from "zod";

export const UnknownRecord = z.record(z.string(), z.unknown());
export const DecimalString = z.string();
export const NullableDecimalString = z.string().nullish();
export const DecimalInput = z.union([z.string(), z.number()]);

export const StanceSchema = z.enum([
  "support",
  "oppose",
  "qualify",
  "conditional_accept",
  "abstain",
]);
export type Stance = z.infer<typeof StanceSchema>;

export const TurnStanceSchema = z.enum([
  "support",
  "oppose",
  "qualify",
  "conditional_accept",
]);

export const PhaseSchema = z.enum([
  "draft",
  "position_formation",
  "debate",
  "negotiation",
  "compromise",
  "closed",
]);

export const ConflictStatusSchema = z.enum(["open", "resolved", "deadlocked"]);

export const ProposalClassSchema = z.enum([
  "statutory_benefit_change",
  "budget_frame",
  "service_catalogue",
  "fee_schedule",
  "hospital_plan",
  "other",
]);

export const ConsensusOutcomeSchema = z.enum([
  "consensus",
  "partial",
  "veto_blocked",
  "unresolved",
]);

export const PackageStateSchema = z.enum([
  "draft",
  "composed",
  "assessed",
  "published",
  "abandoned",
]);

export const FeasibilityLevelSchema = z.enum(["low", "medium", "high", "unknown"]);

export const BasisKindSchema = z.enum([
  "measured",
  "derived",
  "modelled",
  "assumed",
  "not_estimated",
]);

export const UncertaintyLabelSchema = z.enum(["evidenced", "modelled", "assumed"]);

export const ClaimTypeSchema = z.enum([
  "quantitative",
  "legal",
  "causal",
  "qualitative",
]);

export const SpeakerKindSchema = z.enum(["institution", "person", "anonymous"]);

export const AttributionStrengthSchema = z.enum(["explicit", "reported", "mention"]);

export const PowerSourceKindSchema = z.enum([
  "statutory",
  "contractual",
  "regulatory",
  "budgetary",
  "unspecified",
]);

export const InstitutionCategorySchema = z.enum([
  "payer",
  "provider",
  "professional_body",
  "patient_representation",
  "ministry",
  "regulator",
  "insurer_association",
  "hospital_operator",
  "other",
]);

export const StanceLabelSchema = z.enum([
  "supporting",
  "contradicting",
  "contextual",
  "tangential",
]);

export const AuthorityTierSchema = z.enum([
  "official_statistics",
  "legislation",
  "scientific_study",
  "institutional_statement",
  "press_report",
  "other",
]);

export const SourceTypeSchema = z.enum([
  "official_statistics",
  "legislation",
  "scientific_study",
  "institutional_statement",
  "press_report",
  "other",
  "unknown",
]);

export const BudgetPeriodSchema = z.enum(["annual", "biennial", "per_run"]);

export const DerivationInputKindSchema = z.enum([
  "reference_figure",
  "passage",
  "tally",
]);

export const JobStatusSchema = z.enum([
  "queued",
  "running",
  "paused",
  "completed",
  "failed",
  "dead_letter",
  "cancelled",
  "budget_exhausted",
]);

export const GuardDecisionSchema = z.enum(["accept", "rewrite", "reject"]);

export const TopicOutcomeKindSchema = z.enum([
  "recommendation",
  "blocked",
  "open_dispute",
]);

export const LastEventIdSchema = z.union([z.string(), z.number()]).transform(String);
