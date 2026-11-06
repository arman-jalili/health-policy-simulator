import { request } from "@/lib/http";

import {
  AllowlistSchema,
  DiscloseProvenanceBodySchema,
  GuardCheckBodySchema,
  GuardCheckResponseSchema,
  ProvenanceSchema,
  ViolationListSchema,
  type DiscloseProvenanceBody,
  type GuardCheckBody,
} from "./contracts";

export async function listViolations(
  filter: { readonly runId?: string; readonly violationClass?: string; readonly limit?: number },
  signal?: AbortSignal,
) {
  const query = new URLSearchParams();
  if (filter.runId !== undefined) query.set("run_id", filter.runId);
  if (filter.violationClass !== undefined) query.set("class", filter.violationClass);
  if (filter.limit !== undefined) query.set("limit", String(filter.limit));
  const suffix = query.size === 0 ? "" : `?${query.toString()}`;
  return request(`/governance/violations${suffix}`, {
    schema: ViolationListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getAllowlist(signal?: AbortSignal) {
  return request("/governance/allowlist", {
    schema: AllowlistSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function checkText(body: GuardCheckBody) {
  return request("/governance/check", {
    schema: GuardCheckResponseSchema,
    method: "POST",
    body: GuardCheckBodySchema.parse(body),
  });
}

export async function getProvenance(positionId: string, version?: number, signal?: AbortSignal) {
  const query = version === undefined ? "" : `?version=${version}`;
  return request(`/positions/${encodeURIComponent(positionId)}/provenance${query}`, {
    schema: ProvenanceSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function discloseProvenance(positionId: string, body: DiscloseProvenanceBody) {
  return request(`/positions/${encodeURIComponent(positionId)}/provenance`, {
    schema: ProvenanceSchema,
    method: "POST",
    body: DiscloseProvenanceBodySchema.parse(body),
  });
}
