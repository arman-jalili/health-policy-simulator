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
