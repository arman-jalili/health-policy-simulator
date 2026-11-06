
export function GET(): Response {
  const apiKey = process.env.HPS_API_KEY;
  return Response.json({
    baseUrl: process.env.HPS_API_BASE_URL ?? "http://127.0.0.1:8000",
    hasApiKey: apiKey !== undefined && apiKey.trim() !== "",
    timeoutMs: 20_000,
  });
}
