import { request } from "@/lib/http";

import {
  AuthorityRuleListSchema,
  PassageSchema,
  SnapshotSchema,
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
