import { proxyJson } from "@/lib/proxy";

export const runtime = "nodejs";

/** Proxy GET /api/v1/demo/support-requests */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const qs = url.searchParams.toString();
  const path = `/api/v1/demo/support-requests${qs ? `?${qs}` : ""}`;
  return proxyJson(path, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
}
