import { request } from "@/lib/http";

import {
  CitePowerSourceBodySchema,
  CitePowerSourceResponseSchema,
  HistoricalPositionBodySchema,
  HistoricalPositionsResponseSchema,
  RegisterStakeholderBodySchema,
  RegisterStakeholderResponseSchema,
  StakeholdersResponseSchema,
  type CitePowerSourceBody,
  type HistoricalPositionBody,
  type RegisterStakeholderBody,
} from "./contracts";

export async function listStakeholders(signal?: AbortSignal) {
  return request("/stakeholders", {
    schema: StakeholdersResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function listHistory(
  stakeholderId: string,
  usableOnly: boolean,
  signal?: AbortSignal,
) {
  return request(
    `/stakeholders/${encodeURIComponent(stakeholderId)}/history?usable_only=${usableOnly ? "true" : "false"}`,
    {
      schema: HistoricalPositionsResponseSchema,
      ...(signal === undefined ? {} : { signal }),
    },
  );
}

export async function recordHistoricalPosition(
  stakeholderId: string,
  body: HistoricalPositionBody,
) {
  return request(`/stakeholders/${encodeURIComponent(stakeholderId)}/history`, {
    schema: HistoricalPositionsResponseSchema,
    method: "POST",
    body: HistoricalPositionBodySchema.parse(body),
  });
}

export async function citePowerSource(stakeholderId: string, body: CitePowerSourceBody) {
  return request(`/stakeholders/${encodeURIComponent(stakeholderId)}/powers`, {
    schema: CitePowerSourceResponseSchema,
    method: "POST",
    body: CitePowerSourceBodySchema.parse(body),
  });
}

export async function registerStakeholder(body: RegisterStakeholderBody) {
  return request("/stakeholders", {
    schema: RegisterStakeholderResponseSchema,
    method: "POST",
    body: RegisterStakeholderBodySchema.parse(body),
  });
}
