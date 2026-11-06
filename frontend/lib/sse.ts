import { ApiError, ErrorBodySchema, proxyPath } from "@/lib/http";

export interface SseFrame {
  readonly event: string;
  readonly id: string | null;
  readonly data: string;
}

export interface SseOptions {
  readonly lastEventId?: string;
  readonly signal?: AbortSignal;
  readonly onFrame: (frame: SseFrame) => void;
  readonly onError?: (error: ApiError) => void;
  readonly onClose?: () => void;
}

function parseFrame(block: string): SseFrame | null {
  let event = "message";
  let id: string | null = null;
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line === "" || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    const rawValue = colon === -1 ? "" : line.slice(colon + 1);
    const value = rawValue.startsWith(" ") ? rawValue.slice(1) : rawValue;
    if (field === "event") event = value;
    else if (field === "id") id = value;
    else if (field === "data") data.push(value);
  }
  if (data.length === 0 && event === "message") return null;
  return { event, id, data: data.join("\n") };
}

export function openEventStream(path: string, options: SseOptions): () => void {
  const controller = new AbortController();
  const forwardAbort = (): void => controller.abort();
  if (options.signal !== undefined) {
    if (options.signal.aborted) controller.abort();
    else options.signal.addEventListener("abort", forwardAbort, { once: true });
  }

  const run = async (): Promise<void> => {
    try {
      const headers: Record<string, string> = { Accept: "text/event-stream" };
      if (options.lastEventId !== undefined && options.lastEventId !== "") {
        headers["Last-Event-ID"] = options.lastEventId;
      }
      const response = await fetch(proxyPath(path), {
        method: "GET",
        headers,
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) {
        const text = await response.text().catch(() => "");
        let code = `HTTP_${response.status}`;
        let message = response.statusText || `HTTP ${response.status}`;
        let traceId = response.headers.get("x-request-id") ?? "";
        try {
          const parsed = ErrorBodySchema.safeParse(JSON.parse(text));
          if (parsed.success) {
            code = parsed.data.code;
            message = parsed.data.message;
            traceId = parsed.data.trace_id;
          }
        } catch {
          // keep the HTTP fallback
        }
        options.onError?.(new ApiError({ status: response.status, code, message, traceId }));
        return;
      }
      if (response.body === null) {
        options.onClose?.();
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let separator = buffer.indexOf("\n\n");
        while (separator !== -1) {
          const block = buffer.slice(0, separator);
          buffer = buffer.slice(separator + 2);
          const frame = parseFrame(block);
          if (frame !== null) options.onFrame(frame);
          separator = buffer.indexOf("\n\n");
        }
      }
      options.onClose?.();
    } catch (error) {
      if (controller.signal.aborted) return;
      if (error instanceof ApiError) {
        options.onError?.(error);
        return;
      }
      options.onError?.(
        new ApiError({
          status: 0,
          code: "STREAM_ERROR",
          message: "Der Ereignisstrom wurde unterbrochen.",
        }),
      );
    } finally {
      options.signal?.removeEventListener("abort", forwardAbort);
    }
  };

  void run();
  return () => controller.abort();
}
