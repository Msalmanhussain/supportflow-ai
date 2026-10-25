import { NextResponse } from "next/server";

import type { ApiErrorPayload } from "@/lib/types";
import { proxyJson } from "@/lib/proxy";

export const runtime = "nodejs";

type Params = { params: Promise<{ id: string }> };

export async function PATCH(request: Request, { params }: Params) {
  const { id } = await params;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    const payload: ApiErrorPayload = {
      detail: {
        code: "validation_error",
        message: "Request body must be JSON.",
      },
    };
    return NextResponse.json(payload, { status: 422 });
  }

  return proxyJson(`/api/v1/demo/support-requests/${encodeURIComponent(id)}/draft`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });
}
