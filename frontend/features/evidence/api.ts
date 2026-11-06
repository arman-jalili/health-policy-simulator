import { request } from "@/lib/http";

import {
  AssemblePackBodySchema,
  EvidencePackSchema,
  ReweightPackBodySchema,
  ScoreBreakdownSchema,
  SearchCandidatesBodySchema,
  SearchCandidatesResponseSchema,
  type AssemblePackBody,
  type ReweightPackBody,
  type SearchCandidatesBody,
} from "./contracts";

export async function getEvidencePack(packId: string, signal?: AbortSignal) {
  return request(`/evidence/packs/${encodeURIComponent(packId)}`, {
    schema: EvidencePackSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getPackScores(packId: string, signal?: AbortSignal) {
  return request(`/evidence/packs/${encodeURIComponent(packId)}/scores`, {
    schema: ScoreBreakdownSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function searchCandidates(body: SearchCandidatesBody, signal?: AbortSignal) {
  return request("/evidence/candidates", {
    schema: SearchCandidatesResponseSchema,
    method: "POST",
    body: SearchCandidatesBodySchema.parse(body),
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function assemblePack(body: AssemblePackBody) {
  return request("/evidence/packs", {
    schema: EvidencePackSchema,
    method: "POST",
    body: AssemblePackBodySchema.parse(body),
  });
}

export async function reweightPack(packId: string, body: ReweightPackBody) {
  return request(`/evidence/packs/${encodeURIComponent(packId)}/reweight`, {
    schema: EvidencePackSchema,
    method: "POST",
    body: ReweightPackBodySchema.parse(body),
  });
}
