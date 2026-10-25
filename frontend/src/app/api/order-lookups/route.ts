import { NextResponse } from "next/server";

import type { ApiErrorPayload, OrderLookupRequest } from "@/lib/types";

export const runtime = "nodejs";

/**
 * Thin proxy to FastAPI POST /api/v1/demo/order-lookups.
 * Does not duplicate ownership checks or database access.
 */
export async function POST(request: Request) {
  const baseUrl = process.env.FASTAPI_BASE_URL?.trim();
  if (!baseUrl) {
    const payload: ApiErrorPayload = {
      detail: {
        code: "backend_unavailable",
        message:
          "FASTAPI_BASE_URL is not configured on the Next.js server. Set it in frontend/.env.local.",
      },
    };
    return NextResponse.json(payload, { status: 503 });
  }

  let body: OrderLookupRequest;
  try {
    body = (await request.json()) as OrderLookupRequest;
  } catch {
    const payload: ApiErrorPayload = {
      detail: {
        code: "validation_error",
        message: "Request body must be JSON with order_id and customer_email.",
      },
    };
    return NextResponse.json(payload, { status: 422 });
  }

  const target = `${baseUrl.replace(/\/$/, "")}/api/v1/demo/order-lookups`;

  try {
    const upstream = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        order_id: body.order_id,
        customer_email: body.customer_email,
      }),
      cache: "no-store",
    });

    const text = await upstream.text();
    let data: unknown = null;
    if (text) {
      try {
        data = JSON.parse(text) as unknown;
      } catch {
        const payload: ApiErrorPayload = {
          detail: {
            code: "backend_unavailable",
            message: "The order API returned a non-JSON response.",
          },
        };
        return NextResponse.json(payload, { status: 503 });
      }
    }

    return NextResponse.json(data, { status: upstream.status });
  } catch {
    const payload: ApiErrorPayload = {
      detail: {
        code: "backend_unavailable",
        message:
          "Could not reach the SupportFlow FastAPI backend. Confirm Docker services are running and FASTAPI_BASE_URL is correct.",
      },
    };
    return NextResponse.json(payload, { status: 503 });
  }
}
