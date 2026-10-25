#!/usr/bin/env python3
"""End-to-end policy draft evaluation with a real local model.

Records classification errors separately from retrieval errors.
Keyword retrieval is not semantic search. Prompt injection is not claimed solved.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import clear_settings_cache  # noqa: E402
from app.services.ollama_client import OllamaError, reset_ollama_client  # noqa: E402
from app.services.support_draft import build_support_draft  # noqa: E402

CASES_PATH = ROOT / "docs" / "evaluation" / "policy_cases.json"
RESULTS_PATH = ROOT / "docs" / "evaluation" / "policy_eval_results.md"


def _retrieval_ok(case: dict, actual_section_ids: list[str], outcome: str | None) -> bool:
    expected_ids = case.get("expected_section_ids") or []
    expected_outcome = case["expected_outcome"]
    if expected_outcome == "draft_ready":
        if outcome != "draft_ready":
            return False
        # Primary expected section must appear among retrieved sources.
        if not expected_ids:
            return len(actual_section_ids) == 0
        return expected_ids[0] in actual_section_ids
    # Handoff / review paths: sources must be empty for these fixtures.
    return outcome == expected_outcome and actual_section_ids == []


async def run_eval(base_url: str, model: str) -> int:
    os.environ["OLLAMA_BASE_URL"] = base_url
    os.environ["OLLAMA_MODEL"] = model
    clear_settings_cache()
    reset_ollama_client()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    rows: list[dict] = []
    latencies: list[float] = []

    for case in cases:
        started = time.perf_counter()
        error = None
        actual_intent = None
        actual_outcome = None
        actual_section_ids: list[str] = []
        review = None
        sources_empty = None
        try:
            result = await build_support_draft(message=case["message"])
            actual_intent = result.classification.intent
            actual_outcome = result.outcome
            actual_section_ids = [s.section_id for s in result.sources]
            review = result.requires_human_review
            sources_empty = len(result.sources) == 0
            # Sanity: draft text must contain each source body when present.
            for source in result.sources:
                if source.text not in result.draft_text:
                    error = "source_text_missing_from_draft"
                    break
        except OllamaError as exc:
            error = f"{exc.code}: {exc.message}"
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)

        class_ok = (
            actual_intent == case["expected_intent"] if error is None else False
        )
        retrieval_ok = (
            _retrieval_ok(case, actual_section_ids, actual_outcome)
            if error is None
            else False
        )
        # When classification is wrong, still score retrieval against what ran.
        review_ok = review is True if error is None else False

        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "expected_intent": case["expected_intent"],
                "actual_intent": actual_intent,
                "class_ok": class_ok,
                "expected_outcome": case["expected_outcome"],
                "actual_outcome": actual_outcome,
                "expected_sections": ",".join(case.get("expected_section_ids") or [])
                or "—",
                "actual_sections": ",".join(actual_section_ids) or "—",
                "retrieval_ok": retrieval_ok,
                "review_ok": review_ok,
                "sources_empty": sources_empty,
                "latency_ms": round(elapsed_ms, 1),
                "error": error or "",
            }
        )

    class_hits = sum(1 for r in rows if r["class_ok"])
    retrieval_hits = sum(1 for r in rows if r["retrieval_ok"])
    review_hits = sum(1 for r in rows if r["review_ok"])
    errors = sum(1 for r in rows if r["error"])
    avg = sum(latencies) / len(latencies) if latencies else 0
    ordered = sorted(latencies)
    p95 = ordered[int(0.95 * (len(ordered) - 1))] if ordered else 0

    lines = [
        "# Policy draft real-model evaluation (Phase 2.3)",
        "",
        f"- Model: `{model}`",
        f"- Ollama base URL: `{base_url}` (no secrets)",
        f"- Cases: {len(rows)}",
        f"- Classification matches: **{class_hits}/{len(rows)}**",
        f"- Retrieval/outcome matches: **{retrieval_hits}/{len(rows)}**",
        f"- Mandatory review OK: **{review_hits}/{len(rows)}**",
        f"- Transport/errors: **{errors}/{len(rows)}**",
        f"- Latency avg ms: {avg:.1f}",
        f"- Latency ~p95 ms: {p95:.1f}",
        "",
        "Classification errors are counted separately from retrieval errors.",
        "Keyword retrieval is **not** semantic search. Prompt injection is **not** solved.",
        "",
        "| id | category | expected intent | actual intent | class OK | expected outcome | actual outcome | expected sections | actual sections | retrieval OK | review OK | latency_ms | error |",
        "|----|----------|-----------------|---------------|----------|------------------|----------------|-------------------|-----------------|--------------|-----------|------------|-------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['expected_intent']} | {r['actual_intent']} | "
            f"{r['class_ok']} | {r['expected_outcome']} | {r['actual_outcome']} | "
            f"{r['expected_sections']} | {r['actual_sections']} | {r['retrieval_ok']} | "
            f"{r['review_ok']} | {r['latency_ms']} | {r['error']} |"
        )
    lines.append("")
    RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"Wrote {RESULTS_PATH} class={class_hits}/{len(rows)} "
        f"retrieval={retrieval_hits}/{len(rows)} review={review_hits}/{len(rows)} "
        f"errors={errors} avg_ms={avg:.1f} p95_ms={p95:.1f}"
    )
    return 0 if errors == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "qwen3:1.7b"),
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_eval(args.base_url, args.model)))


if __name__ == "__main__":
    main()
