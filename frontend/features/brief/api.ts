import { request } from "@/lib/http";

import {
  BriefResponseSchema,
  BriefVersionListSchema,
  CitationListSchema,
  VersionBriefBodySchema,
  VersionBriefResponseSchema,
} from "./contracts";

export async function publishBrief(runId: string) {
  return request(`/runs/${encodeURIComponent(runId)}/brief`, {
    schema: BriefResponseSchema,
    method: "POST",
  });
}

export async function listBriefVersions(runId: string, signal?: AbortSignal) {
  return request(`/runs/${encodeURIComponent(runId)}/briefs`, {
    schema: BriefVersionListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getBrief(briefId: string, signal?: AbortSignal) {
  return request(`/briefs/${encodeURIComponent(briefId)}`, {
    schema: BriefResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function createBriefVersion(briefId: string, reason: string) {
  return request(`/briefs/${encodeURIComponent(briefId)}:version`, {
    schema: VersionBriefResponseSchema,
    method: "POST",
    body: VersionBriefBodySchema.parse({ reason }),
  });
}

export async function listCitations(briefId: string, section?: string, signal?: AbortSignal) {
  const query = section === undefined ? "" : `?section=${encodeURIComponent(section)}`;
  return request(`/briefs/${encodeURIComponent(briefId)}/citations${query}`, {
    schema: CitationListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}
