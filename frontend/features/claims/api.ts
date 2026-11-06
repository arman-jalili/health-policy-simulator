import { request } from "@/lib/http";

import {
  ClaimDetailSchema,
  ClaimVerdictSchema,
  ContradictionResponseSchema,
  FlagBodySchema,
  ReferenceFigureBodySchema,
  ReferenceFigureSchema,
  ReferenceFiguresResponseSchema,
  ReviewBodySchema,
  VerifyClaimBodySchema,
  type ReferenceFigureBody,
  type VerifyClaimBody,
} from "./contracts";

export async function verifyClaim(body: VerifyClaimBody) {
  return request("/claims:verify", {
    schema: ClaimVerdictSchema,
    method: "POST",
    body: VerifyClaimBodySchema.parse(body),
  });
}

export async function getClaim(claimId: string, signal?: AbortSignal) {
  return request(`/claims/${encodeURIComponent(claimId)}`, {
    schema: ClaimDetailSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function flagClaim(claimId: string, reason: string) {
  return request(`/claims/${encodeURIComponent(claimId)}:flag`, {
    schema: ClaimVerdictSchema,
    method: "POST",
    body: FlagBodySchema.parse({ reason }),
  });
}

export async function reviewClaim(claimId: string, verdict: string, basis: string) {
  return request(`/claims/${encodeURIComponent(claimId)}/reviews`, {
    schema: ClaimVerdictSchema,
    method: "POST",
    body: ReviewBodySchema.parse({ verdict, basis }),
  });
}

export async function getContradictions(signal?: AbortSignal) {
  return request("/contradictions", {
    schema: ContradictionResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function listReferenceFigures(signal?: AbortSignal) {
  return request("/reference-figures", {
    schema: ReferenceFiguresResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function createReferenceFigure(body: ReferenceFigureBody) {
  return request("/reference-figures", {
    schema: ReferenceFigureSchema,
    method: "POST",
    body: ReferenceFigureBodySchema.parse(body),
  });
}
