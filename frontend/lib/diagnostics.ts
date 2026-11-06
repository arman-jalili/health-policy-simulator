export interface FailedRequest {
  readonly method: string;
  readonly path: string;
  readonly status: number;
  readonly code: string;
  readonly traceId: string;
  readonly at: string;
}

type Listener = (items: readonly FailedRequest[]) => void;

const LIMIT = 20;
const buffer: FailedRequest[] = [];
const listeners = new Set<Listener>();

export function recordFailure(entry: Omit<FailedRequest, "at">): void {
  buffer.unshift({ ...entry, at: new Date().toISOString() });
  if (buffer.length > LIMIT) buffer.length = LIMIT;
  for (const listener of listeners) listener([...buffer]);
}

export function failedRequests(): readonly FailedRequest[] {
  return [...buffer];
}

export function subscribeFailures(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export interface DiagnosticsPayload {
  readonly generatedAt: string;
  readonly userAgent: string;
  readonly settings: unknown;
  readonly readiness: unknown;
  readonly failedRequests: readonly FailedRequest[];
}

export function buildDiagnostics(input: {
  readonly settings: unknown;
  readonly readiness: unknown;
}): DiagnosticsPayload {
  return {
    generatedAt: new Date().toISOString(),
    userAgent: typeof navigator === "undefined" ? "server" : navigator.userAgent,
    settings: redactSettings(input.settings),
    readiness: input.readiness,
    failedRequests: failedRequests(),
  };
}

function redactSettings(settings: unknown): unknown {
  if (typeof settings !== "object" || settings === null) return settings;
  const clone: Record<string, unknown> = { ...(settings as Record<string, unknown>) };
  for (const key of Object.keys(clone)) {
    if (/key|secret|token|password/i.test(key)) clone[key] = "[redacted]";
  }
  return clone;
}
