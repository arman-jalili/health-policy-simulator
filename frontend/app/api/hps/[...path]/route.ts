import type { NextRequest } from "next/server";


const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "content-type",
  "last-event-id",
  "idempotency-key",
  "x-request-id",
] as const;

const FORWARDED_RESPONSE_HEADERS = [
  "content-type",
  "cache-control",
  "x-request-id",
  "x-trace-id",
  "x-accel-buffering",
] as const;

function upstreamBase(): string {
  const configured = process.env.HPS_API_BASE_URL ?? "http://127.0.0.1:8000";
  return configured.replace(/\/+$/, "");
}

function encodeSegment(segment: string): string {
  return encodeURIComponent(segment).replace(/%3A/gi, ":");
}

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (path.length === 0) {
    return Response.json(
      {
        code: "PROXY_PATH_MISSING",
        message: "The proxy requires a backend path.",
        details: [],
        trace_id: "",
      },
      { status: 400 },
    );
  }
  const platform = path[0] === "_platform";
  const segments = platform ? path.slice(1) : path;
  const target = new URL(request.url);
  const upstreamUrl = `${upstreamBase()}${platform ? "" : "/api/v1"}/${segments
    .map(encodeSegment)
    .join("/")}${target.search}`;

  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  headers.set("accept", request.headers.get("accept") ?? "application/json");
  const apiKey = process.env.HPS_API_KEY;
  if (apiKey !== undefined && apiKey.trim() !== "") headers.set("X-API-Key", apiKey);

  const method = request.method.toUpperCase();
  const init: RequestInit = {
    method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };
  if (method !== "GET" && method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, init);
  } catch {
    return Response.json(
      {
        code: "PROXY_UPSTREAM_UNREACHABLE",
        message: "The backend service is unreachable.",
        details: [{ message: upstreamUrl }],
        trace_id: "",
      },
      { status: 503 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value !== null) responseHeaders.set(name, value);
  }
  responseHeaders.set(
    "content-type",
    upstream.headers.get("content-type") ?? "application/json; charset=utf-8",
  );
  responseHeaders.set("cache-control", "no-store");

  return new Response(method === "HEAD" ? null : upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
export const HEAD = forward;
