import { z } from "zod";

import {
  ConflictStatusSchema,
  DecimalInput,
  DecimalString,
  JobStatusSchema,
  PhaseSchema,
  ProposalClassSchema,
  StanceSchema,
  TurnStanceSchema,
  UnknownRecord,
} from "@/features/contracts";

export const BoundStakeholderSchema = z.object({
  stakeholder_id: z.string(),
  institution_name: z.string(),
  institution_code: z.string(),
  profile_version: z.string(),
  persona_version: z.string(),
});
export type BoundStakeholder = z.infer<typeof BoundStakeholderSchema>;

export const OpenRunBodySchema = z.object({
  question: z.string().min(1).max(4000),
  round_cap: z.number().int().min(1).max(50).optional(),
  stakeholder_ids: z.array(z.string()).optional(),
  consensus_threshold: z.number().gt(0).max(1).optional(),
});
export type OpenRunBody = z.infer<typeof OpenRunBodySchema>;

export const OpenRunResponseSchema = z.object({
  run_id: z.string(),
  phase: PhaseSchema,
  mandate_hash: z.string(),
  bound: z.array(BoundStakeholderSchema),
});
export type OpenRunResponse = z.infer<typeof OpenRunResponseSchema>;

export const RunResponseSchema = z.object({
  run_id: z.string(),
  phase: PhaseSchema,
  round: z.number().int(),
  round_cap: z.number().int(),
  closed: z.boolean(),
  bound_stakeholder_ids: z.array(z.string()),
  open_position_ids: z.array(z.string()),
  coalition_ids: z.array(z.string()),
});
export type RunResponse = z.infer<typeof RunResponseSchema>;

export const EventItemSchema = z.object({
  sequence: z.number().int(),
  event_type: z.string(),
  payload: UnknownRecord,
  occurred_at: z.string().nullish(),
});
export type EventItem = z.infer<typeof EventItemSchema>;

export const EventsResponseSchema = z.object({
  items: z.array(EventItemSchema),
  state: RunResponseSchema,
});
export type EventsResponse = z.infer<typeof EventsResponseSchema>;

export const LearningInsightSchema = z.object({
  insight_type: z.string(),
  statement: z.string(),
  derived_from: z.array(z.string()),
  round_number: z.number().int(),
});
export type LearningInsight = z.infer<typeof LearningInsightSchema>;

export const LearningSchema = z.object({
  learning_id: z.string(),
  run_id: z.string(),
  round: z.number().int(),
  insights: z.array(LearningInsightSchema),
});
export type Learning = z.infer<typeof LearningSchema>;

export const RoundSchema = z.object({
  round: z.number().int(),
  closed: z.boolean(),
  argument_count: z.number().int(),
  abstention_count: z.number().int(),
  learning: LearningSchema.nullish(),
});
export type Round = z.infer<typeof RoundSchema>;

export const RoundListSchema = z.object({ items: z.array(RoundSchema) });
export type RoundList = z.infer<typeof RoundListSchema>;

export const OpenRoundBodySchema = z.object({ round: z.number().int().min(1).optional() });
export const OpenRoundResponseSchema = z.object({
  run_id: z.string(),
  round: z.number().int(),
  closed: z.boolean(),
  turn_order: z.array(z.string()),
});
export type OpenRoundResponse = z.infer<typeof OpenRoundResponseSchema>;

export const LearningInsightInputSchema = z.object({
  insight_type: z.string().min(1),
  statement: z.string().min(1).max(5000),
  derived_from: z.array(z.string()).default([]),
  round_number: z.number().int().min(0).default(0),
});

export const CloseRoundBodySchema = z.object({
  learning: z.array(LearningInsightInputSchema).default([]),
  convergence: z.string().max(64).default("none"),
});
export type CloseRoundBody = z.infer<typeof CloseRoundBodySchema>;

export const StoppingConditionSchema = z
  .object({
    name: z.string(),
    fired: z.boolean(),
    parameters: UnknownRecord,
  })
  .catchall(z.unknown());

export const CloseRoundResponseSchema = z.object({
  run_id: z.string(),
  round: z.number().int(),
  learning: LearningSchema,
  stopping_condition: StoppingConditionSchema,
});
export type CloseRoundResponse = z.infer<typeof CloseRoundResponseSchema>;

export const ProposalComponentInputSchema = z.object({
  measure: z.string().min(1).max(2000),
  effect: z.string().min(1).max(2000),
  population: z.string().min(1).max(500),
  cost_eur: DecimalInput.nullish(),
  quantification: z.enum(["quantified", "unquantified"]).default("quantified"),
  support_record: z.array(z.string()).default([]),
});
export type ProposalComponentInput = z.infer<typeof ProposalComponentInputSchema>;

export const ProposalInputSchema = z.object({
  summary: z.string().min(1).max(2000),
  components: z.array(ProposalComponentInputSchema).default([]),
});
export type ProposalInput = z.infer<typeof ProposalInputSchema>;

export const ProposalComponentOutputSchema = z.object({
  measure: z.string(),
  effect: z.string(),
  population: z.string(),
  cost_eur: z.string().nullish(),
  quantification: z.enum(["quantified", "unquantified"]),
  support_record: z.array(z.string()),
});
export type ProposalComponentOutput = z.infer<typeof ProposalComponentOutputSchema>;

export const ProposalOutputSchema = z.object({
  summary: z.string(),
  components: z.array(ProposalComponentOutputSchema),
});
export type ProposalOutput = z.infer<typeof ProposalOutputSchema>;

export const PositionBodySchema = z.object({
  stakeholder_id: z.string(),
  topic: z.string().min(1),
  stance: TurnStanceSchema,
  proposal: ProposalInputSchema,
  evidence_ids: z.array(z.string()).default([]),
});
export type PositionBody = z.infer<typeof PositionBodySchema>;

export const RevisionReasonSchema = z.object({
  argument_ids: z.array(z.string()),
  pack_ids: z.array(z.string()),
  driver: z.string(),
});
export type RevisionReason = z.infer<typeof RevisionReasonSchema>;

export const PositionResponseSchema = z.object({
  position_id: z.string(),
  run_id: z.string(),
  round: z.number().int(),
  stakeholder_id: z.string(),
  topic: z.string(),
  stance: StanceSchema,
  proposal: ProposalOutputSchema,
  evidence_ids: z.array(z.string()),
  supersedes: z.string().nullish(),
  revision: RevisionReasonSchema.nullish(),
});
export type PositionResponse = z.infer<typeof PositionResponseSchema>;

export const TargetSchema = z.object({
  topic: z.string().min(1),
  position_id: z.string().nullish(),
  argument_id: z.string().nullish(),
});
export const TargetInputSchema = z.object({
  topic: z.string().min(1),
  position_id: z.string().optional(),
  argument_id: z.string().optional(),
});
export type TargetInput = z.infer<typeof TargetInputSchema>;

export const ClaimInputSchema = z.object({
  text: z.string().min(1).max(2000),
  claim_id: z.string().nullish(),
  verdict: z.string().nullish(),
});

export const TurnBodySchema = z.object({
  stakeholder_id: z.string(),
  target: TargetInputSchema,
  stance: TurnStanceSchema,
  text: z.string().min(1).max(8000),
  claims: z.array(ClaimInputSchema).default([]),
  evidence_ids: z.array(z.string()).default([]),
  unsupported: z.boolean().default(false),
  invocation_id: z.string().nullish(),
});
export type TurnBody = z.infer<typeof TurnBodySchema>;

export const ArgumentResponseSchema = z.object({
  argument_id: z.string(),
  run_id: z.string(),
  round: z.number().int(),
  stakeholder_id: z.string(),
  target: TargetSchema,
  stance: z.string(),
  evidence_ids: z.array(z.string()),
  unsupported: z.boolean(),
  invocation_id: z.string().nullish(),
});
export type ArgumentResponse = z.infer<typeof ArgumentResponseSchema>;

export const ReviseBodySchema = z.object({
  stance: TurnStanceSchema,
  reason: z.object({
    argument_ids: z.array(z.string()).default([]),
    pack_ids: z.array(z.string()).default([]),
    driver: z.string().max(2000).default(""),
  }),
});
export type ReviseBody = z.infer<typeof ReviseBodySchema>;

export const AbstentionBodySchema = z.object({
  stakeholder_id: z.string(),
  topic: z.string().min(1),
});
export type AbstentionBodyInput = z.infer<typeof AbstentionBodySchema>;

export const ConflictSchema = z.object({
  conflict_id: z.string(),
  run_id: z.string(),
  topic: z.string(),
  status: ConflictStatusSchema,
  stances: z.record(z.string(), z.string()),
});
export type Conflict = z.infer<typeof ConflictSchema>;

export const ConflictListSchema = z.object({ items: z.array(ConflictSchema) });

export const CoalitionOfferSchema = z.object({
  offer_id: z.string(),
  invited_id: z.string(),
  conditions: z.string(),
  status: z.enum(["offered", "accepted", "declined"]),
  decline_reason: z.string().nullish(),
});

export const CoalitionBodySchema = z.object({
  topic: z.string().min(1),
  member_ids: z.array(z.string()).min(1),
  proposal: ProposalInputSchema,
});
export type CoalitionBody = z.infer<typeof CoalitionBodySchema>;

export const CoalitionResponseSchema = z.object({
  coalition_id: z.string(),
  run_id: z.string(),
  topic: z.string(),
  proposal: ProposalOutputSchema,
  members: z.array(z.string()),
  offers: z.array(CoalitionOfferSchema),
});
export type CoalitionResponse = z.infer<typeof CoalitionResponseSchema>;

export const SelectionBodySchema = z.object({ mandate: z.string().min(1) });
export type SelectionBody = z.infer<typeof SelectionBodySchema>;
export const SelectionResponseSchema = z.object({
  items: z.array(
    z.object({
      stakeholder_id: z.string(),
      materiality: z.number().min(0).max(1),
    }),
  ),
});
export type SelectionResponse = z.infer<typeof SelectionResponseSchema>;

export const BindBodySchema = z.object({ stakeholder_ids: z.array(z.string()).min(1) });
export type BindBody = z.infer<typeof BindBodySchema>;
export const BindResponseSchema = z.object({
  bindings: z.array(
    z.object({
      binding_id: z.string(),
      stakeholder_id: z.string(),
      persona_version: z.string(),
    }),
  ),
});

export const BudgetSchema = z.object({
  max_invocations: z.number().int().min(0).nullish(),
  max_tokens: z.number().int().min(0).nullish(),
  max_cost: DecimalInput.nullish(),
});
export type Budget = z.infer<typeof BudgetSchema>;

export const StartBodySchema = z.object({ budget: BudgetSchema.default({}) });
export type StartBody = z.infer<typeof StartBodySchema>;
export const StartResponseSchema = z.object({
  job_id: z.string(),
  run_id: z.string(),
  status: z.string(),
});
export type StartResponse = z.infer<typeof StartResponseSchema>;

export const PauseResumeBodySchema = z.object({
  action: z.enum(["pause", "resume"]),
  reason: z.string().default("client_request"),
  budget: BudgetSchema.nullish(),
});
export type PauseResumeBody = z.infer<typeof PauseResumeBodySchema>;
export const PauseResumeResponseSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  checkpoint_round: z.number().int().nullish(),
  checkpoint_phase: z.string().nullish(),
});
export type PauseResumeResponse = z.infer<typeof PauseResumeResponseSchema>;

export const StakeholderUsageSchema = z.object({
  stakeholder: z.string(),
  invocations: z.number().int(),
  input_tokens: z.number().int(),
  output_tokens: z.number().int(),
  cost: DecimalString,
});
export type StakeholderUsage = z.infer<typeof StakeholderUsageSchema>;

export const RoundUsageSchema = z.object({
  round: z.number().int(),
  invocations: z.number().int(),
  input_tokens: z.number().int(),
  output_tokens: z.number().int(),
  cost: DecimalString,
});
export type RoundUsage = z.infer<typeof RoundUsageSchema>;

export const UsageResponseSchema = z.object({
  run_id: z.string(),
  total_invocations: z.number().int(),
  input_tokens: z.number().int(),
  output_tokens: z.number().int(),
  cost: DecimalString,
  by_stakeholder: z.array(StakeholderUsageSchema),
  by_round: z.array(RoundUsageSchema),
  model: z.string().optional(),
  provider: z.string().optional(),
});
export type UsageResponse = z.infer<typeof UsageResponseSchema>;

export const GraphStateSchema = z.object({
  run_id: z.string(),
  round: z.number().int(),
  phase: z.string(),
  next_actor: z.string().nullish(),
  budget_used_invocations: z.number().int(),
  budget_used_tokens: z.number().int(),
  budget_used_cost: DecimalString,
});
export type GraphState = z.infer<typeof GraphStateSchema>;

export const JobResponseSchema = z.object({
  job_id: z.string(),
  run_id: z.string(),
  status: JobStatusSchema,
  attempts: z.number().int(),
  checkpoint: GraphStateSchema,
  error: z.string().nullable(),
  progress_sequence: z.number().int(),
});
export type JobResponse = z.infer<typeof JobResponseSchema>;

export const ProgressEventSchema = z.object({
  event_id: z.union([z.string(), z.number()]).transform(String),
  run_id: z.string(),
  sequence: z.number().int(),
  kind: z.string(),
  payload: UnknownRecord,
});
export type ProgressEvent = z.infer<typeof ProgressEventSchema>;

export const ProposalClassList = ProposalClassSchema.options;
