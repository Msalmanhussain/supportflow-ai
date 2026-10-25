"use client";

import { FormEvent, useId, useRef, useState } from "react";

import type {
  ApiErrorPayload,
  LookupUiState,
  OrderLookupSuccess,
} from "@/lib/types";
import styles from "./OrderLookupForm.module.css";

function isSuccess(data: unknown): data is OrderLookupSuccess {
  if (!data || typeof data !== "object") return false;
  const value = data as Record<string, unknown>;
  return (
    typeof value.order_id === "string" &&
    typeof value.status === "string" &&
    typeof value.last_update === "string" &&
    value.is_simulated === true
  );
}

function displayOptional(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }
  return value;
}

export default function OrderLookupForm() {
  const orderIdFieldId = useId();
  const emailFieldId = useId();
  const noticeId = useId();
  const statusRegionId = useId();

  const [orderId, setOrderId] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [uiState, setUiState] = useState<LookupUiState>({ kind: "idle" });
  const requestSeq = useRef(0);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const seq = ++requestSeq.current;
    // Clear any previous result immediately so stale data cannot linger.
    setUiState({ kind: "loading" });

    try {
      const response = await fetch("/api/order-lookups", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          order_id: orderId,
          customer_email: customerEmail,
        }),
      });

      const data: unknown = await response.json().catch(() => null);

      // Ignore out-of-order responses from an older request.
      if (seq !== requestSeq.current) {
        return;
      }

      if (response.status === 200 && isSuccess(data)) {
        setUiState({ kind: "success", order: data });
        return;
      }

      const errorPayload = data as ApiErrorPayload | null;
      const code = errorPayload?.detail?.code;
      const message =
        errorPayload?.detail?.message ??
        "The order lookup could not be completed.";

      if (response.status === 404 || code === "order_not_found") {
        setUiState({ kind: "not_found", message });
        return;
      }

      if (response.status === 422 || code === "validation_error") {
        setUiState({ kind: "validation", message });
        return;
      }

      setUiState({
        kind: "unavailable",
        message:
          code === "backend_unavailable"
            ? message
            : "The order service is temporarily unavailable. Try again after confirming the API is running.",
      });
    } catch {
      if (seq !== requestSeq.current) {
        return;
      }
      setUiState({
        kind: "unavailable",
        message:
          "Could not reach the SupportFlow frontend proxy. Confirm the Next.js server is running.",
      });
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="lookup-heading">
      <h2 id="lookup-heading" className={styles.sectionTitle}>
        Order lookup
      </h2>
      <p id={noticeId} className={styles.notice}>
        Demo using simulated orders. Email matching is a demonstration check
        only, not production authentication. For AI-assisted drafts, use the
        customer message section below.
      </p>

      <form className={styles.form} onSubmit={onSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor={orderIdFieldId}>Order ID</label>
          <input
            id={orderIdFieldId}
            name="order_id"
            type="text"
            autoComplete="off"
            value={orderId}
            onChange={(event) => setOrderId(event.target.value)}
            aria-describedby={noticeId}
            required
          />
        </div>

        <div className={styles.field}>
          <label htmlFor={emailFieldId}>Customer email</label>
          <input
            id={emailFieldId}
            name="customer_email"
            type="email"
            autoComplete="email"
            value={customerEmail}
            onChange={(event) => setCustomerEmail(event.target.value)}
            aria-describedby={noticeId}
            required
          />
        </div>

        <button type="submit" className={styles.button} disabled={uiState.kind === "loading"}>
          {uiState.kind === "loading" ? "Checking…" : "Check order"}
        </button>
      </form>

      <div
        id={statusRegionId}
        className={styles.status}
        role="status"
        aria-live="polite"
      >
        {uiState.kind === "idle" && (
          <p className={styles.muted}>Enter an order ID and email to look up a simulated order.</p>
        )}

        {uiState.kind === "loading" && <p>Looking up order…</p>}

        {uiState.kind === "validation" && (
          <p className={styles.error} role="alert">
            {uiState.message}
          </p>
        )}

        {uiState.kind === "not_found" && (
          <p className={styles.error} role="alert">
            {uiState.message}
          </p>
        )}

        {uiState.kind === "unavailable" && (
          <p className={styles.error} role="alert">
            {uiState.message}
          </p>
        )}

        {uiState.kind === "success" && (
          <div className={styles.result}>
            <p className={styles.simulated}>
              Simulated data — not live courier tracking
            </p>
            <dl className={styles.details}>
              <div>
                <dt>Order ID</dt>
                <dd>{uiState.order.order_id}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{uiState.order.status}</dd>
              </div>
              <div>
                <dt>Courier</dt>
                <dd>{displayOptional(uiState.order.courier)}</dd>
              </div>
              <div>
                <dt>Estimated delivery</dt>
                <dd>{displayOptional(uiState.order.estimated_delivery)}</dd>
              </div>
              <div>
                <dt>Last update</dt>
                <dd>{uiState.order.last_update}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </section>
  );
}
