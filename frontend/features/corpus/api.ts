import { request } from "@/lib/http";

import {
  AuthorityRuleListSchema,
  DocumentIngestionResponseSchema,
  DocumentStageResponseSchema,
  IngestDocumentBodySchema,
  IngestionRunSchema,
  PassageSchema,
  PinSnapshotBodySchema,
  PinSnapshotResponseSchema,
  SnapshotSchema,
  StartIngestionRunBodySchema,
  StartIngestionRunResponseSchema,
  type IngestDocumentBody,
  type PinSnapshotBody,
  type StartIngestionRunBody,
} from "./contracts";

export async function getSnapshot(snapshotId: string, signal?: AbortSignal) {
  return request(`/corpus/snapshots/${encodeURIComponent(snapshotId)}`, {
    schema: SnapshotSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getPassage(passageId: string, signal?: AbortSignal) {
  return request(`/passages/${encodeURIComponent(passageId)}`, {
    schema: PassageSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getAuthorityRules(claimType?: string, signal?: AbortSignal) {
  const query = claimType === undefined ? "" : `?claim_type=${encodeURIComponent(claimType)}`;
  return request(`/corpus/authority-rules${query}`, {
    schema: AuthorityRuleListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function startIngestionRun(body: StartIngestionRunBody) {
  return request("/corpus/ingestion-runs", {
    schema: StartIngestionRunResponseSchema,
    method: "POST",
    body: StartIngestionRunBodySchema.parse(body),
    timeoutMs: 900_000,
  });
}

export async function getIngestionRun(runId: string, signal?: AbortSignal) {
  return request(`/corpus/ingestion-runs/${encodeURIComponent(runId)}`, {
    schema: IngestionRunSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function pinSnapshot(body: PinSnapshotBody) {
  return request("/corpus/snapshots", {
    schema: PinSnapshotResponseSchema,
    method: "POST",
    body: PinSnapshotBodySchema.parse(body),
  });
}

export async function ingestDocument(body: IngestDocumentBody) {
  return request("/corpus/documents", {
    schema: DocumentIngestionResponseSchema,
    method: "POST",
    body: IngestDocumentBodySchema.parse(body),
    timeoutMs: 120_000,
  });
}

export async function publishDocument(documentId: string) {
  return request(`/corpus/documents/${encodeURIComponent(documentId)}:publish`, {
    schema: DocumentStageResponseSchema,
    method: "POST",
    timeoutMs: 120_000,
  });
}
