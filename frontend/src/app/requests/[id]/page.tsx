"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import SiteNav from "@/components/SiteNav";
import type { ApiErrorPayload, SupportRequestDetail } from "@/lib/types";
import styles from "./page.module.css";

type Ui =
  | { kind: "loading" }
  | { kind: "missing"; message: string }
  | { kind: "error"; message: string }
  | { kind: "ready"; detail: SupportRequestDetail };

export default function RequestDetailPage() {
  const params = useParams<{ id: string }>();
  const requestId = params.id;

  const [ui, setUi] = useState<Ui>({ kind: "loading" });
  const [editor, setEditor] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const actionLock = useRef(false);

  const load = useCallback(async () => {
    setUi({ kind: "loading" });
    setBanner(null);
    try {
      const response = await fetch(`/api/support-requests/${requestId}`, {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      if (response.status === 404) {
        setUi({
          kind: "missing",
          message: "This support request was not found.",
        });
        return;
      }
      if (!response.ok || !payload || typeof payload !== "object") {
        const err = payload as ApiErrorPayload | null;
        setUi({
          kind: "error",
          message: err?.detail?.message ?? "Could not load this request.",
        });
        return;
      }
      const detail = payload as SupportRequestDetail;
      setUi({ kind: "ready", detail });
      setEditor(detail.draft_current);
    } catch {
      setUi({ kind: "error", message: "Could not reach the frontend proxy." });
    }
  }, [requestId]);

  useEffect(() => {
    void load();
  }, [load]);

  const dirty =
    ui.kind === "ready" && editor.trim() !== ui.detail.draft_current.trim();
  const pending = ui.kind === "ready" && ui.detail.review_status === "pending_review";

  async function runMutation(
    path: string,
    method: "PATCH" | "POST",
    body: Record<string, unknown>,
  ) {
    if (actionLock.current || ui.kind !== "ready") return;
    actionLock.current = true;
    setBusy(true);
    setBanner(null);
    try {
      const response = await fetch(path, {
        method,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(body),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (response.status === 409) {
        const err = payload as ApiErrorPayload | null;
        setBanner(
          (err?.detail?.message ?? "Revision conflict.") +
            " Reload the current record before continuing.",
        );
        return;
      }
      if (!response.ok) {
        const err = payload as ApiErrorPayload | null;
        setBanner(err?.detail?.message ?? "The review action failed.");
        return;
      }
      const detail = payload as SupportRequestDetail;
      setUi({ kind: "ready", detail });
      setEditor(detail.draft_current);
      setNote("");
    } catch {
      setBanner("Could not reach the frontend proxy.");
    } finally {
      setBusy(false);
      actionLock.current = false;
    }
  }

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <SiteNav />
        <h1 className={styles.title}>Support request</h1>
        <p className={styles.notice} role="note">
          Approval records a local review decision. Nothing is sent.
        </p>
        <p className={styles.simulated}>
          Simulated data — not live courier tracking · single-operator local demo
          (no authenticated reviewer identity)
        </p>

        {ui.kind === "loading" && <p className={styles.muted}>Loading…</p>}
        {ui.kind === "missing" && (
          <p className={styles.error} role="alert">
            {ui.message}
          </p>
        )}
        {ui.kind === "error" && (
          <p className={styles.error} role="alert">
            {ui.message}
          </p>
        )}
        {banner && (
          <p className={styles.error} role="alert" data-testid="conflict-banner">
            {banner}{" "}
            <button
              type="button"
              className={styles.buttonSecondary}
              data-testid="reload-request"
              onClick={() => void load()}
            >
              Reload
            </button>
          </p>
        )}

        {ui.kind === "ready" && (
          <>
            <section className={styles.section}>
              <h2>Status</h2>
              <dl className={styles.meta}>
                <div>
                  <dt>Review status</dt>
                  <dd data-testid="detail-review-status">
                    {ui.detail.review_status}
                  </dd>
                </div>
                <div>
                  <dt>Outcome</dt>
                  <dd>{ui.detail.outcome}</dd>
                </div>
                <div>
                  <dt>Intent</dt>
                  <dd>{ui.detail.classification.intent}</dd>
                </div>
                <div>
                  <dt>Revision</dt>
                  <dd>{ui.detail.revision}</dd>
                </div>
                <div>
                  <dt>Model / prompt</dt>
                  <dd>
                    {ui.detail.model_id} · {ui.detail.prompt_version}
                  </dd>
                </div>
              </dl>
            </section>

            <section className={styles.section}>
              <h2>Original message</h2>
              <pre className={styles.pre}>{ui.detail.message}</pre>
              {ui.detail.customer_email && (
                <p className={styles.muted}>Email: {ui.detail.customer_email}</p>
              )}
            </section>

            <section className={styles.section}>
              <h2>Original generated draft</h2>
              <pre className={styles.pre}>{ui.detail.draft_original}</pre>
            </section>

            <section className={styles.section}>
              <h2>Editable draft</h2>
              {pending ? (
                <>
                  <label htmlFor="editable-draft" className={styles.muted}>
                    Pending draft text
                  </label>
                  <textarea
                    id="editable-draft"
                    className={styles.textarea}
                    value={editor}
                    onChange={(event) => setEditor(event.target.value)}
                    disabled={busy}
                    maxLength={10000}
                    data-testid="editable-draft"
                  />
                  {dirty && (
                    <p className={styles.muted} data-testid="unsaved-warning">
                      Unsaved changes — save before approving.
                    </p>
                  )}
                  <div className={styles.note}>
                    <label htmlFor="review-note">Optional reviewer note</label>
                    <input
                      id="review-note"
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                      disabled={busy}
                      maxLength={2000}
                    />
                  </div>
                  <div className={styles.actions}>
                    <button
                      type="button"
                      className={styles.button}
                      disabled={busy || !dirty}
                      data-testid="save-draft"
                      onClick={() =>
                        void runMutation(
                          `/api/support-requests/${requestId}/draft`,
                          "PATCH",
                          {
                            draft_text: editor,
                            expected_revision: ui.detail.revision,
                          },
                        )
                      }
                    >
                      Save changes
                    </button>
                    <button
                      type="button"
                      className={styles.button}
                      disabled={busy || dirty}
                      data-testid="approve-draft"
                      title={
                        dirty
                          ? "Save changes before approving"
                          : "Approve current draft"
                      }
                      onClick={() =>
                        void runMutation(
                          `/api/support-requests/${requestId}/approve`,
                          "POST",
                          {
                            expected_revision: ui.detail.revision,
                            note: note || null,
                          },
                        )
                      }
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className={`${styles.button} ${styles.buttonDanger}`}
                      disabled={busy}
                      data-testid="reject-draft"
                      onClick={() =>
                        void runMutation(
                          `/api/support-requests/${requestId}/reject`,
                          "POST",
                          {
                            expected_revision: ui.detail.revision,
                            note: note || null,
                          },
                        )
                      }
                    >
                      Reject
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <pre className={styles.pre}>{ui.detail.draft_current}</pre>
                  {ui.detail.reviewed_text && (
                    <>
                      <h2>Approved text snapshot</h2>
                      <pre className={styles.pre} data-testid="reviewed-text">
                        {ui.detail.reviewed_text}
                      </pre>
                    </>
                  )}
                  <p className={styles.muted} data-testid="readonly-notice">
                    This request is read-only after approval or rejection.
                  </p>
                </>
              )}
            </section>

            {ui.detail.sources.length > 0 && (
              <section className={styles.section} data-testid="detail-policy-sources">
                <h2>Policy evidence</h2>
                {ui.detail.sources.map((source) => (
                  <div
                    key={`${source.document_id}:${source.section_id}`}
                    className={styles.sourceItem}
                  >
                    <p>
                      <strong>
                        {source.title} · v{source.version} · {source.section_id}
                      </strong>
                    </p>
                    <p className={styles.muted}>{source.demo_label}</p>
                    <pre className={styles.pre}>{source.text}</pre>
                  </div>
                ))}
              </section>
            )}

            <section className={styles.section}>
              <h2>Review events</h2>
              <ol className={styles.events}>
                {ui.detail.events.map((event) => (
                  <li key={event.id}>
                    {event.action} · rev {event.revision} · {event.created_at}
                    {event.note ? ` — ${event.note}` : ""}
                  </li>
                ))}
              </ol>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
