#!/usr/bin/env python3
"""Real-model classification evaluation (host → local Ollama).

Does not run inside CI by default. Requires Ollama + pulled model.
Never prints secrets. Customer texts are synthetic fixtures only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Allow `python scripts/eval_classification.py` from repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import clear_settings_cache  # noqa: E402
from app.services.classification import classify_message  # noqa: E402
from app.services.ollama_client import OllamaClient, OllamaError, reset_ollama_client  # noqa: E402

CASES_PATH = ROOT / "docs" / "evaluation" / "classification_cases.json"
RESULTS_PATH = ROOT / "docs" / "evaluation" / "classification_eval_results.md"


async def run_eval(base_url: str, model: str) -> int:
    import os

    os.environ["OLLAMA_BASE_URL"] = base_url
    os.environ["OLLAMA_MODEL"] = model
    clear_settings_cache()
    reset_ollama_client()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    client = OllamaClient()
    rows: list[dict] = []
    latencies: list[float] = []

    try:
        for case in cases:
            started = time.perf_counter()
            error = None
            actual_intent = None
            actual_order_id = None
            actual_review = None
            try:
                result = await classify_message(case["message"], client=client)
                actual_intent = result.intent
                actual_order_id = result.order_id
                actual_review = result.requires_human_review
            except OllamaError as exc:
                error = f"{exc.code}: {exc.message}"
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies.append(elapsed_ms)

            intent_ok = actual_intent == case["expected_intent"] if error is None else False
            order_ok = (
                (actual_order_id or None) == (case.get("expected_order_id") or None)
                if error is None
                else False
            )
            review_ok = (
                actual_review is True
                if case["expected_intent"] in {"refund_request", "other"}
                else (actual_review is False or actual_review is True)
            )
            if case["expected_intent"] in {"refund_request", "other"}:
                review_ok = actual_review is True if error is None else False
            elif error is None:
                # For clear order_status / return_policy, review may be false;
                # still record actual value.
                review_ok = True

            rows.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "expected_intent": case["expected_intent"],
                    "actual_intent": actual_intent,
                    "intent_match": intent_ok,
                    "expected_order_id": case.get("expected_order_id"),
                    "actual_order_id": actual_order_id,
                    "order_match": order_ok,
                    "review_ok": review_ok,
                    "latency_ms": round(elapsed_ms, 1),
                    "error": error,
                }
            )
    finally:
        await client.aclose()

    matched_intent = sum(1 for r in rows if r["intent_match"])
    matched_order = sum(1 for r in rows if r["order_match"])
    matched_review = sum(1 for r in rows if r["review_ok"])
    errors = sum(1 for r in rows if r["error"])
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p95 = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0.0

    lines = [
        "# Classification real-model evaluation",
        "",
        f"- Model: `{model}`",
        f"- Ollama base URL: `{base_url}` (no secrets)",
        f"- Cases: {len(rows)}",
        f"- Intent matches: {matched_intent}/{len(rows)}",
        f"- Order ID matches: {matched_order}/{len(rows)}",
        f"- Review-rule OK: {matched_review}/{len(rows)}",
        f"- Errors: {errors}/{len(rows)}",
        f"- Latency avg ms: {avg_latency:.1f}",
        f"- Latency ~p95 ms: {p95:.1f}",
        "",
        "| id | category | expected intent | actual intent | intent OK | expected order | actual order | order OK | review OK | latency_ms | error |",
        "|----|----------|-----------------|---------------|-----------|----------------|--------------|----------|-----------|------------|-------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['expected_intent']} | {r['actual_intent']} | "
            f"{r['intent_match']} | {r['expected_order_id']} | {r['actual_order_id']} | "
            f"{r['order_match']} | {r['review_ok']} | {r['latency_ms']} | {r['error'] or ''} |"
        )
    lines.append("")
    lines.append(
        "These results are from a real local model run. Mocked unit tests do not "
        "prove model reliability."
    )
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {RESULTS_PATH}")
    print(
        f"intent={matched_intent}/{len(rows)} order={matched_order}/{len(rows)} "
        f"review={matched_review}/{len(rows)} errors={errors} "
        f"avg_ms={avg_latency:.1f} p95_ms={p95:.1f}"
    )
    return 0 if errors == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Host Ollama URL",
    )
    parser.add_argument("--model", default="qwen3:1.7b")
    args = parser.parse_args()
    return asyncio.run(run_eval(args.base_url, args.model))


if __name__ == "__main__":
    raise SystemExit(main())
