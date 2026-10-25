# Learning note — Phase 2.3 grounded policy retrieval

Study this after the Phase 2.3 stop report.

## Goal

Answer `return_policy` questions using **verbatim** text from a small fictional demo policy collection, selected by **deterministic keyword/token matching**. Not embeddings, not semantic search, not legal advice.

## Documents (`app/policy_docs/`)

| File | `document_id` | Sections |
|------|---------------|----------|
| `demo-returns.md` | `demo-pol-returns` | `eligibility-window`, `return-process`, `non-returnable` |
| `demo-refunds.md` | `demo-pol-refunds` | `refund-processing` |
| `demo-exchanges.md` | `demo-pol-exchanges` | `exchanges` |

Each file has front matter: `document_id`, `title`, `version`, `demo_label` (explicit DEMO POLICY wording). Sections use `## section: <id>` plus a `###` title and body.

Loaded only from the fixed directory `app/policy_docs/` (bundled in the Docker image via `COPY app`). Customer text never selects filesystem paths.

## Matching rules

Implemented in `app/services/policy_retrieval.py`:

1. Tokenize the message; also check multi-word aliases as substrings.
2. Each `section_id` has an explicit alias set (topic aliases).
3. Score = count of distinct matching aliases (**not** calibrated confidence).
4. Drop scores `< MIN_SCORE` (1); sort by score / ids; return at most `MAX_RESULTS` (3).
5. Empty result → workflow `needs_human_review` (no invented rules).

## Files

| Path | Role |
|------|------|
| `app/policy_docs/*.md` | Fictional policy corpus |
| `app/services/policy_loader.py` | Parse/load Markdown from fixed dir |
| `app/services/policy_retrieval.py` | Keyword retrieval |
| `app/services/draft_templates.py` | `draft_return_policy_ready` / no-match |
| `app/services/support_draft.py` | `return_policy` branch uses retrieval |
| `app/schemas/support_draft.py` | `PolicySource` + `sources` on response |
| `tests/test_policy_retrieval.py` | Loader/matching tests |
| `scripts/eval_policy_e2e.py` | Real-model e2e eval |

## Data flow (return_policy)

1. Model classifies only (message text; no docs/email/orders to the model).
2. If intent ≠ `return_policy`, `sources` stays `[]` (refund stays handoff).
3. If `return_policy`: `retrieve_policy_sections(message)`.
4. No hits → `needs_human_review` + empty sources.
5. Hits → `draft_ready` template quoting verbatim section text + `sources` citations.
6. Application still forces `requires_human_review: true` and `is_simulated: true`.

## Response `sources` shape

`document_id`, `title`, `version`, `section_id`, `section_title`, `text` (verbatim body), `demo_label`.

## Tests and honesty

- Unit tests cover topics, bounds, no-match, verbatim sources, path-injection messages, refund handoff without policy authorization.
- E2e eval (`docs/evaluation/policy_eval_results.md`) records **classification** vs **retrieval** errors separately.
- Do not claim prompt injection is solved or that keyword retrieval is semantic search.
