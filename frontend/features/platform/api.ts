import { fetchPlatformHead, request } from "@/lib/http";

import { HealthSchema, ReadyzSchema } from "./contracts";

export async function getHealth(signal?: AbortSignal) {
  return request("/_platform/healthz", {
    schema: HealthSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getReadyz(signal?: AbortSignal) {
  return request("/_platform/readyz", {
    schema: ReadyzSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function headOpenApi(signal?: AbortSignal): Promise<boolean> {
  return fetchPlatformHead("/openapi.json", signal);
}
