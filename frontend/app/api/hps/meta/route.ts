// Runtime configuration for the operator UI.
//
// `await connection()` is load-bearing: with Cache Components enabled this route was prerendered at
// build time and baked the build host's defaults into the image, so inside Docker it reported
// `http://127.0.0.1:8000` while the container environment said `http://backend:8000`.
// (`export const dynamic = "force-dynamic"` is rejected when `cacheComponents` is on.)
import { connection } from "next/server";

export async function GET(): Promise<Response> {
  await connection();
  const apiKey = process.env.HPS_API_KEY;
  return Response.json({
    baseUrl: process.env.HPS_API_BASE_URL ?? "http://127.0.0.1:8000",
    hasApiKey: apiKey !== undefined && apiKey.trim() !== "",
    timeoutMs: 20_000,
  });
}
