"use client";

import Link from "next/link";
import { FormEvent, useId, useRef, useState } from "react";

import type {
  ApiErrorPayload,
  DraftUiState,
  SupportDraftSuccess,
} from "@/lib/types";
import styles from "./SupportDraftForm.module.css";

function isDraftSuccess(data: unknown): data is SupportDraftSuccess {
  if (!data || typeof data !== "object") return false;
  const value = data as Record<string, unknown>;
  const classification = value.classification;
  if (!classification || typeof classification !== "object") return false;
  const cls = classification as Record<string, unknown>;
  const sources = value.sources;
  return (
    typeof value.draft_text === "string" &&
    typeof value.outcome === "string" &&
    value.requires_human_review === true &&
    value.is_simulated === true &&
    typeof cls.intent === "string" &&
    Array.isArray(sources) &&
    typeof value.id === "string" &&
    typeof value.revision === "number" &&
    typeof value.review_status === "string"
  );
}

function outcomeLabel(outcome: SupportDraftSuccess["outcome"]): string {
  switch (outcome) {
    case "draft_ready":
      return "Draft ready";
    case "needs_information":
      return "Needs information";
    case "needs_human_review":
      return "Needs human review";
    default:
      return outcome;
  }
}

export default function SupportDraftForm() {
  const messageFieldId = useId();
  const emailFieldId = useId();
  const noticeId = useId();
  const approvalId = useId();
  const statusRegionId = useId();

  const [message, setMessage] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [uiState, setUiState] = useState<DraftUiState>({ kind: "idle" });
  const requestSeq = useRef(0);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (uiState.kind === "loading") {
      return;
    }

    const seq = ++requestSeq.current;
    setUiState({ kind: "loading" });

    const trimmedEmail = customerEmail.trim();
    const payload: Record<string, string> = { message };
    if (trimmedEmail) {
      payload.customer_email = trimmedEmail;
    }

    try {
      const response = await fetch("/api/support-drafts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(payload),
      });

      const data: unknown = await response.json().catch(() => null);

      if (seq !== requestSeq.current) {
        return;
      }

      if (response.status === 200 && isDraftSuccess(data)) {
        setUiState({ kind: "success", draft: data });
        return;
      }

      const errorPayload = data as ApiErrorPayload | null;
      const code = errorPayload?.detail?.code;
      const messageText =
        errorPayload?.detail?.message ??
        "The support draft could not be generated.";

      if (response.status === 422 || code === "validation_error") {
        setUiState({ kind: "validation", message: messageText });
        return;
      }

      setUiState({
        kind: "unavailable",
        message:
          code === "backend_unavailable" ||
          code === "backend_timeout" ||
          code === "ollama_unavailable" ||
          code === "ollama_timeout" ||
          code === "ollama_model_missing" ||
          code === "ollama_invalid_output"
            ? messageText
            : "The draft service is temporarily unavailable. Confirm the API and Ollama are running.",
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

  const loading = uiState.kind === "loading";

  return (
    <section className={styles.panel} aria-labelledby="draft-heading">
      <h2 id="draft-heading" className={styles.sectionTitle}>
        Customer message draft
      </h2>
      <p id={noticeId} className={styles.notice}>
        Simulated data only. The local model classifies the message; application
        code looks up verified order facts, retrieves fictional demo policy
        sections by keyword matching, and fills a template. Classification is
        advisory, not authorization. Keyword scores are not confidence.
      </p>
      <p id={approvalId} className={styles.approvalNotice} role="note">
        Draft — human approval required
      </p>

      <form className={styles.form} onSubmit={onSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor={messageFieldId}>Customer message</label>
          <textarea
            id={messageFieldId}
            name="message"
            rows={5}
            maxLength={2000}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            aria-describedby={`${noticeId} ${approvalId}`}
            data-testid="draft-message"
            required
          />
        </div>

        <div className={styles.field}>
          <label htmlFor={emailFieldId}>Customer email (optional)</label>
          <p id={`${emailFieldId}-hint`} className={styles.hint}>
            Required before any order lookup. Demo ownership check only.
          </p>
          <input
            id={emailFieldId}
            name="customer_email"
            type="email"
            autoComplete="email"
            value={customerEmail}
            onChange={(event) => setCustomerEmail(event.target.value)}
            aria-describedby={`${emailFieldId}-hint`}
            data-testid="draft-email"
          />
        </div>

        <button
          type="submit"
          className={styles.button}
          disabled={loading}
          data-testid="draft-submit"
        >
          {loading ? "Generating…" : "Generate draft"}
        </button>
      </form>

      <div
        id={statusRegionId}
        className={styles.status}
        role="status"
        aria-live="polite"
      >
        {uiState.kind === "idle" && (
          <p className={styles.muted}>
            Enter a customer message to classify and generate a review-only draft.
          </p>
        )}

        {uiState.kind === "loading" && (
          <p data-testid="draft-loading">
            Classifying and preparing draft… this can take several seconds on CPU.
          </p>
        )}

        {uiState.kind === "validation" && (
          <p className={styles.error} role="alert" data-testid="draft-error">
            {uiState.message}
          </p>
        )}

        {uiState.kind === "unavailable" && (
          <p className={styles.error} role="alert" data-testid="draft-error">
            {uiState.message}
          </p>
        )}

        {uiState.kind === "success" && (
          <div className={styles.result} data-testid="draft-success">
            <p className={styles.approvalNotice} role="note">
              Draft — human approval required
            </p>
            <p className={styles.simulated}>
              Simulated data — not live courier tracking · not sent to the customer
            </p>
            <dl className={styles.meta}>
              <div>
                <dt>Classified intent</dt>
                <dd data-testid="draft-intent">
                  {uiState.draft.classification.intent}
                </dd>
              </div>
              <div>
                <dt>Extracted order ID (model)</dt>
                <dd>{uiState.draft.classification.order_id ?? "None"}</dd>
              </div>
              <div>
                <dt>Outcome</dt>
                <dd data-testid="draft-outcome">
                  {outcomeLabel(uiState.draft.outcome)}
                </dd>
              </div>
              <div>
                <dt>Review status</dt>
                <dd data-testid="draft-review-status">
                  {uiState.draft.review_status}
                </dd>
              </div>
            </dl>
            <p className={styles.openReview}>
              <Link
                href={`/requests/${uiState.draft.id}`}
                data-testid="open-review-link"
              >
                Open in review queue (rev {uiState.draft.revision})
              </Link>
            </p>
            <p className={styles.draftLabel}>Draft reply</p>
            <pre className={styles.draftText} data-testid="draft-text">
              {uiState.draft.draft_text}
            </pre>

            {uiState.draft.sources.length > 0 && (
              <div className={styles.sources} data-testid="policy-sources">
                <p className={styles.draftLabel}>Policy sources</p>
                <ul className={styles.sourceList}>
                  {uiState.draft.sources.map((source) => (
                    <li
                      key={`${source.document_id}:${source.section_id}`}
                      className={styles.sourceItem}
                    >
                      <p className={styles.sourceMeta}>
                        {source.title} · v{source.version} · section{" "}
                        {source.section_id}
                      </p>
                      <p className={styles.sourceDemo}>{source.demo_label}</p>
                      <p className={styles.sourceTitle}>{source.section_title}</p>
                      <pre className={styles.sourceText}>{source.text}</pre>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
