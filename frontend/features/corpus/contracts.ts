import { z } from "zod";

import { AuthorityTierSchema, ClaimTypeSchema, SpeakerKindSchema } from "@/features/contracts";

export const OffsetsSchema = z.object({
  start: z.number().int(),
  end: z.number().int(),
});

export const ProvenanceSchema = z.object({
  outlet: z.string(),
  published_on: z.string(),
  medium: z.string(),
  page_from: z.number().int(),
  page_to: z.number().int(),
  offsets: OffsetsSchema,
  source_uri: z.string(),
});
export type Provenance = z.infer<typeof ProvenanceSchema>;

export const PassageSchema = z.object({
  passage_id: z.string(),
  text: z.string(),
  provenance: ProvenanceSchema,
  speaker_kind: SpeakerKindSchema,
  citable: z.boolean(),
});
export type Passage = z.infer<typeof PassageSchema>;

export const IndexManifestSchema = z.object({
  index_version: z.string(),
  embedding_model: z.string(),
  searchable_since: z.string(),
  passage_count: z.number().int(),
});
export type IndexManifest = z.infer<typeof IndexManifestSchema>;

export const SnapshotSchema = z.object({
  snapshot_id: z.string(),
  label: z.string(),
  manifest_hash: z.string(),
  pinned_at: z.string(),
  document_ids: z.array(z.string()),
  index: IndexManifestSchema,
});
export type Snapshot = z.infer<typeof SnapshotSchema>;

export const AuthorityRuleSchema = z.object({
  claim_type: ClaimTypeSchema,
  ordered_tiers: z.array(AuthorityTierSchema),
});
export type AuthorityRule = z.infer<typeof AuthorityRuleSchema>;

export const AuthorityRuleListSchema = z.array(AuthorityRuleSchema);

export const DocumentSchema = z.object({
  document_id: z.string(),
  source_uri: z.string(),
  content_hash: z.string(),
  publication: z.object({
    outlet: z.string(),
    published_on: z.string(),
    medium: z.string(),
  }),
  source_type: z.string(),
  language: z.object({ tag: z.string() }),
  tier: AuthorityTierSchema.nullable(),
  quality: z
    .object({
      method: z.enum(["native", "ocr"]),
      confidence: z.number(),
      missing_glyph_rate: z.number(),
      page_count: z.number().int(),
    })
    .nullable(),
  citable: z.boolean(),
  articles: z.array(
    z.object({
      article_id: z.string(),
      headline: z.string(),
      is_canonical: z.boolean(),
      page_from: z.number().int(),
      page_to: z.number().int(),
      passage_count: z.number().int(),
    }),
  ),
});
export type Document = z.infer<typeof DocumentSchema>;

export const IngestionOutcomeValueSchema = z.enum(["accepted", "quarantined", "failed"]);
export type IngestionOutcomeValue = z.infer<typeof IngestionOutcomeValueSchema>;

export const IngestionRunStatusSchema = z.enum(["running", "completed", "failed"]);
export type IngestionRunStatus = z.infer<typeof IngestionRunStatusSchema>;

export const IngestionOutcomeSchema = z.object({
  path: z.string(),
  outcome: IngestionOutcomeValueSchema,
  reason: z.string().nullish(),
});
export type IngestionOutcome = z.infer<typeof IngestionOutcomeSchema>;

export const IngestionRunSchema = z.object({
  run_id: z.string(),
  shard_label: z.string(),
  status: IngestionRunStatusSchema,
  attempted: z.number().int(),
  accepted: z.number().int(),
  quarantined: z.number().int(),
  failed: z.number().int(),
  outcomes: z.array(IngestionOutcomeSchema).default([]),
  failure_reason: z.string().nullish(),
});
export type IngestionRun = z.infer<typeof IngestionRunSchema>;

export const StartIngestionRunBodySchema = z.object({
  shard_label: z.string().min(1),
  paths: z.array(z.string().min(1)).min(1),
});
export type StartIngestionRunBody = z.infer<typeof StartIngestionRunBodySchema>;

export const StartIngestionRunResponseSchema = z.object({
  run_id: z.string(),
  status: IngestionRunStatusSchema,
});
export type StartIngestionRunResponse = z.infer<typeof StartIngestionRunResponseSchema>;

export const PinSnapshotBodySchema = z.object({
  label: z.string().min(1),
  document_ids: z.array(z.string().min(1)).optional(),
});
export type PinSnapshotBody = z.infer<typeof PinSnapshotBodySchema>;

export const PinSnapshotResponseSchema = z.object({
  snapshot_id: z.string(),
  manifest_hash: z.string(),
});
export type PinSnapshotResponse = z.infer<typeof PinSnapshotResponseSchema>;

export const SOURCE_TYPES = [
  "official_statistics",
  "legislation",
  "scientific_study",
  "institutional_statement",
  "press_report",
  "other",
] as const;

export const SourceTypeSchema = z.enum(SOURCE_TYPES);
export type SourceType = z.infer<typeof SourceTypeSchema>;

export const IngestDocumentBodySchema = z.object({
  source_uri: z.string().min(1),
  publication: z.object({
    outlet: z.string().min(1),
    published_on: z.string().min(1),
    medium: z.string().min(1),
  }),
  source_type: SourceTypeSchema,
});
export type IngestDocumentBody = z.infer<typeof IngestDocumentBodySchema>;

export const ExtractionQualitySchema = z.object({
  method: z.string(),
  confidence: z.number(),
  missing_glyph_rate: z.number(),
  page_count: z.number().int(),
});
export type ExtractionQuality = z.infer<typeof ExtractionQualitySchema>;

export const DocumentIngestionResponseSchema = z.object({
  document_id: z.string(),
  quality: ExtractionQualitySchema.nullable(),
  citable: z.boolean(),
});
export type DocumentIngestionResponse = z.infer<typeof DocumentIngestionResponseSchema>;

export const DocumentStageResponseSchema = z.object({
  document_id: z.string(),
  citable: z.boolean(),
  article_count: z.number().int().default(0),
  passage_count: z.number().int().default(0),
  index: IndexManifestSchema.nullable(),
});
export type DocumentStageResponse = z.infer<typeof DocumentStageResponseSchema>;
