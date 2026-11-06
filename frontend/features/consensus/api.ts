import { request } from "@/lib/http";

import {
  AssessImpactBodySchema,
  AssessImpactResponseSchema,
  ComparisonResponseSchema,
  ComposePackageBodySchema,
  ComposePackageResponseSchema,
  ConsensusResponseSchema,
  DeriveBodySchema,
  PackageListSchema,
  UnresolvedConflictListSchema,
  type AssessImpactBody,
  type ComposePackageBody,
} from "./contracts";

export async function getConsensus(runId: string, signal?: AbortSignal) {
  return request(`/runs/${encodeURIComponent(runId)}/consensus`, {
    schema: ConsensusResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function deriveConsensus(runId: string, topics: readonly string[]) {
  return request(`/runs/${encodeURIComponent(runId)}/analysis:derive`, {
    schema: ConsensusResponseSchema,
    method: "POST",
    body: DeriveBodySchema.parse({ topics: [...topics] }),
  });
}

export async function getOpenConflicts(runId: string, signal?: AbortSignal) {
  return request(`/runs/${encodeURIComponent(runId)}/conflicts/open`, {
    schema: UnresolvedConflictListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function composePackage(runId: string, body: ComposePackageBody) {
  return request(`/runs/${encodeURIComponent(runId)}/packages`, {
    schema: ComposePackageResponseSchema,
    method: "POST",
    body: ComposePackageBodySchema.parse(body),
  });
}

export async function listPackages(runId: string, signal?: AbortSignal) {
  return request(`/runs/${encodeURIComponent(runId)}/packages`, {
    schema: PackageListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function assessImpact(packageId: string, body: AssessImpactBody) {
  return request(`/packages/${encodeURIComponent(packageId)}/scenarios`, {
    schema: AssessImpactResponseSchema,
    method: "POST",
    body: AssessImpactBodySchema.parse(body),
  });
}

export async function getComparison(packageId: string, signal?: AbortSignal) {
  return request(`/packages/${encodeURIComponent(packageId)}/comparison`, {
    schema: ComparisonResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}
