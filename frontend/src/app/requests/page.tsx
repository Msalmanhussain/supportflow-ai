"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import SiteNav from "@/components/SiteNav";
import type {
  ApiErrorPayload,
  ReviewStatus,
  SupportRequestListResponse,
} from "@/lib/types";
import styles from "./page.module.css";

const FILTERS: Array<{ label: string; value: ReviewStatus | "all" }> = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending_review" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
];

export default function RequestsPage() {
  const [status, setStatus] = useState<ReviewStatus | "all">("pending_review");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<SupportRequestListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({
        page: String(page),
        page_size: "10",
      });
      if (status !== "all") {
        params.set("status", status);
      }
      try {
        const response = await fetch(`/api/support-requests?${params.toString()}`, {
          headers: { Accept: "application/json" },
          cache: "no-store",
        });
        const payload: unknown = await response.json().catch(() => null);
        if (cancelled) return;
        if (!response.ok) {
          const err = payload as ApiErrorPayload | null;
          setError(err?.detail?.message ?? "Could not load support requests.");
          setData(null);
          return;
        }
        setData(payload as SupportRequestListResponse);
      } catch {
        if (!cancelled) {
          setError("Could not reach the frontend proxy.");
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [status, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <SiteNav />
        <h1 className={styles.title}>Review queue</h1>
        <p className={styles.lead}>
          Local single-operator review. Approval records a local review decision.
          Nothing is sent.
        </p>

        <div className={styles.filters} role="group" aria-label="Status filter">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              className={
                status === filter.value
                  ? `${styles.filterBtn} ${styles.filterBtnActive}`
                  : styles.filterBtn
              }
              data-testid={`filter-${filter.value}`}
              aria-pressed={status === filter.value}
              onClick={() => {
                setPage(1);
                setStatus(filter.value);
              }}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {loading && <p className={styles.muted}>Loading…</p>}
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}

        {!loading && !error && data && data.items.length === 0 && (
          <p className={styles.muted}>No requests for this filter.</p>
        )}

        {!loading && data && data.items.length > 0 && (
          <ul className={styles.list} data-testid="request-list">
            {data.items.map((item) => (
              <li
                key={item.id}
                className={styles.item}
                data-testid={`request-item-${item.id}`}
              >
                <Link
                  href={`/requests/${item.id}`}
                  data-testid={`request-link-${item.id}`}
                >
                  {item.message_preview}
                </Link>
                <p className={styles.meta}>
                  {item.review_status} · {item.classification_intent} ·{" "}
                  {item.outcome} · rev {item.revision}
                </p>
              </li>
            ))}
          </ul>
        )}

        {data && data.total > data.page_size && (
          <div className={styles.pager}>
            <button
              type="button"
              className={styles.filterBtn}
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </button>
            <span className={styles.muted}>
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              className={styles.filterBtn}
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
