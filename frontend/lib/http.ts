import { z } from "zod";

import { recordFailure } from "@/lib/diagnostics";

export const ErrorDetailSchema = z
  .object({
    message: z.string(),
    field: z.string().nullish(),
    code: z.string().nullish(),
  })
  .catchall(z.unknown());

export const ErrorBodySchema = z
  .object({
    code: z.string(),
    message: z.string(),
    details: z.array(ErrorDetailSchema).default([]),
    trace_id: z.string(),
  })
  .catchall(z.unknown());

export type ErrorDetail = z.infer<typeof ErrorDetailSchema>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: readonly ErrorDetail[];
  readonly traceId: string;

  constructor(input: {
    status: number;
    code: string;
    message: string;
    details?: readonly ErrorDetail[];
    traceId?: string;
  }) {
    super(input.message);
    this.name = "ApiError";
    this.status = input.status;
    this.code = input.code;
    this.details = input.details ?? [];
    this.traceId = input.traceId ?? "";
  }
}

export interface RequestOptions<T> {
  readonly schema: z.ZodType<T>;
  readonly method?: "GET" | "POST" | "PATCH" | "DELETE" | "HEAD";
  readonly body?: unknown;
  readonly signal?: AbortSignal;
  readonly timeoutMs?: number;
}

export interface VoidRequestOptions {
  readonly method?: "POST" | "PATCH" | "DELETE";
  readonly body?: unknown;
  readonly signal?: AbortSignal;
  readonly timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 20_000;
const PROXY_ROOT = "/api/hps";
const PLATFORM_PREFIX = "_platform";

export function proxyPath(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${PROXY_ROOT}${normalized}`;
}

export function platformPath(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${PROXY_ROOT}/${PLATFORM_PREFIX}${normalized}`;
}

async function execute(
  url: string,
  method: string,
  body: unknown,
  signal: AbortSignal | undefined,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const forwardAbort = (): void => controller.abort();
  if (signal !== undefined) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", forwardAbort, { once: true });
  }
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const init: RequestInit = {
      method,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
    };
    if (body !== undefined) init.body = JSON.stringify(body);
    return await fetch(url, init);
  } catch (error) {
    if (signal?.aborted === true) {
      throw error;
    }
    if (controller.signal.aborted) {
      throw new ApiError({
        status: 0,
        code: "REQUEST_TIMEOUT",
        message: "Die Anfrage hat das Zeitlimit überschritten.",
      });
    }
    throw new ApiError({
      status: 0,
      code: "NETWORK_ERROR",
      message: "Der Dienst ist nicht erreichbar.",
    });
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", forwardAbort);
  }
}

async function failure(
  response: Response,
  path: string,
  method: string,
): Promise<ApiError> {
  const text = await response.text().catch(() => "");
  let envelope: z.infer<typeof ErrorBodySchema> | null = null;
  if (text !== "") {
    try {
      const parsed = ErrorBodySchema.safeParse(JSON.parse(text));
      if (parsed.success) envelope = parsed.data;
    } catch {
      envelope = null;
    }
  }
  const headerTrace =
    response.headers.get("x-request-id") ?? response.headers.get("x-trace-id") ?? "";
  const code = envelope?.code ?? `HTTP_${response.status}`;
  const message =
    envelope?.message ??
    (text.trim() === "" ? response.statusText || `HTTP ${response.status}` : text.slice(0, 400));
  const traceId = envelope?.trace_id ?? headerTrace;
  if (typeof window !== "undefined") {
    recordFailure({ method, path, status: response.status, code, traceId });
  }
  return new ApiError({
    status: response.status,
    code,
    message,
    details: envelope?.details ?? [],
    traceId,
  });
}

export async function request<T>(path: string, options: RequestOptions<T>): Promise<T> {
  const method = options.method ?? "GET";
  const response = await execute(
    proxyPath(path),
    method,
    options.body,
    options.signal,
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  if (!response.ok) throw await failure(response, path, method);
  const text = await response.text();
  if (text === "") {
    throw new ApiError({
      status: response.status,
      code: "EMPTY_RESPONSE",
      message: "Der Dienst hat keine Daten geliefert.",
      traceId: response.headers.get("x-request-id") ?? "",
    });
  }
  let json: unknown;
  try {
    json = JSON.parse(text);
  } catch {
    throw new ApiError({
      status: response.status,
      code: "INVALID_JSON",
      message: "Die Antwort des Dienstes war kein gültiges JSON.",
      traceId: response.headers.get("x-request-id") ?? "",
    });
  }
  const parsed = options.schema.safeParse(json);
  if (!parsed.success) {
    throw new ApiError({
      status: response.status,
      code: "CONTRACT_MISMATCH",
      message: "Die Antwort des Dienstes entspricht nicht dem vereinbarten Schema.",
      details: parsed.error.issues.map((issue) => ({
        message: issue.message,
        field: issue.path.join("."),
        code: issue.code,
      })),
      traceId: response.headers.get("x-request-id") ?? "",
    });
  }
  return parsed.data;
}

export async function requestVoid(path: string, options: VoidRequestOptions = {}): Promise<void> {
  const method = options.method ?? "POST";
  const response = await execute(
    proxyPath(path),
    method,
    options.body,
    options.signal,
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  if (!response.ok) throw await failure(response, path, method);
}

export const ProxyMetaSchema = z.object({
  baseUrl: z.string(),
  hasApiKey: z.boolean(),
  timeoutMs: z.number(),
});

export type ProxyMeta = z.infer<typeof ProxyMetaSchema>;

export async function fetchProxyMeta(signal?: AbortSignal): Promise<ProxyMeta> {
  const response = await execute("/api/hps/meta", "GET", undefined, signal, 5000);
  if (!response.ok) throw await failure(response, "/_meta", "GET");
  const parsed = ProxyMetaSchema.safeParse(await response.json());
  if (!parsed.success) {
    throw new ApiError({
      status: response.status,
      code: "CONTRACT_MISMATCH",
      message: "Die Proxy-Metadaten sind ungültig.",
    });
  }
  return parsed.data;
}

export async function fetchPlatformHead(path: string, signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await execute(platformPath(path), "HEAD", undefined, signal, 5000);
    return response.ok;
  } catch {
    return false;
  }
}
