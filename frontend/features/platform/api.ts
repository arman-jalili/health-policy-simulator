import { fetchPlatformHead, request } from "@/lib/http";

import { HealthSchema, LlmProviderSchema, ReadyzSchema } from "./contracts";

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

export async function getLlmProvider(signal?: AbortSignal) {
  return request("/simulation/provider", {
    schema: LlmProviderSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function selectLlmProvider(provider: string) {
  return request("/simulation/provider", {
    schema: LlmProviderSchema,
    method: "POST",
    body: { provider },
  });
}
