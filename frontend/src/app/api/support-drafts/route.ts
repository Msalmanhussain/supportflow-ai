import { NextResponse } from "next/server";

import type { ApiErrorPayload, SupportDraftRequest } from "@/lib/types";
import { proxyJson } from "@/lib/proxy";

export const runtime = "nodejs";

const UPSTREAM_TIMEOUT_MS = 90_000;

/**
 * Thin proxy to FastAPI POST /api/v1/demo/support-drafts.
 * Forwards Idempotency-Key. Does not classify or approve drafts.
 */
export async function POST(request: Request) {
  let body: SupportDraftRequest;
  try {
    body = (await request.json()) as SupportDraftRequest;
  } catch {
    const payload: ApiErrorPayload = {
      detail: {
        code: "validation_error",
        message: "Request body must be JSON with message (and optional customer_email).",
      },
    };
    return NextResponse.json(payload, { status: 422 });
  }

  const idempotencyKey =
    request.headers.get("Idempotency-Key")?.trim() || crypto.randomUUID();

  return proxyJson("/api/v1/demo/support-drafts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({
      message: body.message,
      customer_email: body.customer_email ?? null,
    }),
    timeoutMs: UPSTREAM_TIMEOUT_MS,
  });
}
