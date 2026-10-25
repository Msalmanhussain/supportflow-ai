"""Deterministic keyword/token policy retrieval (not semantic search).

Matching rules (documented for operators and tests)
-------------------------------------------------
1. Customer text is tokenized to lowercase alphanumeric tokens (and retained
   multi-word alias phrases checked as substrings on the normalized message).
2. Each policy section has an explicit alias/keyword list (topic aliases).
3. Score for a section = number of distinct aliases that match the message
   (phrase match or token match). Scores are ranking aids only — **not**
   calibrated confidence.
4. Sections with score < MIN_SCORE are discarded.
5. Remaining sections are sorted by score descending, then document_id,
   then section_id; at most MAX_RESULTS are returned.
6. If none remain, retrieval returns an empty list (caller → human review).
7. Customer text never selects filesystem paths; only in-memory sections
   loaded from ``app/policy_docs/`` are scored.

This is keyword retrieval, not embeddings or semantic search.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from app.services.policy_loader import PolicySection, get_policy_sections

MAX_RESULTS = 3
MIN_SCORE = 1

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

# Explicit topic aliases per section_id (stable IDs from policy Markdown).
SECTION_ALIASES: dict[str, frozenset[str]] = {
    "eligibility-window": frozenset(
        {
            "return",
            "returns",
            "returning",
            "eligible",
            "eligibility",
            "window",
            "days",
            "30",
            "thirty",
            "unused",
            "condition",
            "tags",
            "return window",
            "how long",
            "within",
        }
    ),
    "return-process": frozenset(
        {
            "process",
            "procedure",
            "steps",
            "authorize",
            "authorization",
            "label",
            "ship",
            "shipping",
            "rma",
            "how to return",
            "start a return",
            "return process",
            "send back",
            "mail back",
        }
    ),
    "non-returnable": frozenset(
        {
            "nonreturnable",
            "non-returnable",
            "not returnable",
            "final sale",
            "finalsale",
            "gift card",
            "gift cards",
            "software",
            "downloadable",
            "personal care",
            "excluded",
            "cannot return",
            "can't return",
            "no returns",
        }
    ),
    "refund-processing": frozenset(
        {
            "refund",
            "refunds",
            "refunding",
            "processing",
            "timeline",
            "business days",
            "original payment",
            "payment method",
            "when will i get",
            "how long for refund",
            "refund process",
            "refund timeline",
            "money back",
        }
    ),
    "exchanges": frozenset(
        {
            "exchange",
            "exchanges",
            "exchanging",
            "swap",
            "size",
            "color",
            "different size",
            "different color",
            "trade",
        }
    ),
}


@dataclass(frozen=True)
class ScoredPolicySection:
    section: PolicySection
    score: int
    matched_aliases: tuple[str, ...]


def tokenize(message: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(message)}


def _normalize_message(message: str) -> str:
    return " ".join(message.casefold().split())


def _alias_matches(alias: str, *, tokens: set[str], normalized: str) -> bool:
    alias_cf = alias.casefold().strip()
    if not alias_cf:
        return False
    if " " in alias_cf or "-" in alias_cf:
        # Phrase / hyphenated alias: substring on normalized whitespace text,
        # and also compare hyphen-stripped form for tokens like non-returnable.
        if alias_cf in normalized:
            return True
        compact = alias_cf.replace("-", " ")
        if compact in normalized:
            return True
        parts = _TOKEN_RE.findall(alias_cf)
        return bool(parts) and all(part in tokens for part in parts)
    return alias_cf in tokens


def score_section(
    section: PolicySection,
    *,
    tokens: set[str],
    normalized: str,
) -> ScoredPolicySection:
    aliases = SECTION_ALIASES.get(section.section_id, frozenset())
    matched: list[str] = []
    for alias in sorted(aliases):
        if _alias_matches(alias, tokens=tokens, normalized=normalized):
            matched.append(alias)
    return ScoredPolicySection(
        section=section,
        score=len(matched),
        matched_aliases=tuple(matched),
    )


def retrieve_policy_sections(
    message: str,
    *,
    sections: Optional[Sequence[PolicySection]] = None,
    max_results: int = MAX_RESULTS,
    min_score: int = MIN_SCORE,
) -> list[ScoredPolicySection]:
    """Return up to ``max_results`` relevant sections for the customer message.

    Does not open files based on ``message``. Does not invent policy text.
    """
    catalog: Iterable[PolicySection]
    if sections is None:
        catalog = get_policy_sections()
    else:
        catalog = sections

    tokens = tokenize(message)
    normalized = _normalize_message(message)
    scored = [
        score_section(section, tokens=tokens, normalized=normalized)
        for section in catalog
    ]
    eligible = [item for item in scored if item.score >= min_score]
    eligible.sort(
        key=lambda item: (
            -item.score,
            item.section.document_id,
            item.section.section_id,
        )
    )
    return eligible[: max(0, max_results)]
