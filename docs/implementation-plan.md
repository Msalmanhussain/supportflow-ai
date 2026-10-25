# Implementation plan — SupportFlow AI

Phased delivery. Status labels: **Implemented**, **Verified**, **Blocked**, **Planned**.

## Phase 1.1 — Repository foundation and environment assessment

| | |
|--|--|
| **Implemented** | Yes |
| **Verified** | Yes |

## Phase 1.2 — FastAPI, PostgreSQL, Docker Compose, synthetic order API

| | |
|--|--|
| **Implemented** | Yes |
| **Verified** | Yes (2026-10-18) |

## Phase 1.3 — Next.js order lookup frontend

| | |
|--|--|
| **Implemented** | Yes (`frontend/`) |
| **Verified** | Yes (2026-10-18) — typecheck, build, proxy success/404/422/503 |

Delivered:

- Next.js 15 App Router + TypeScript page
- Server route proxy `POST /api/order-lookups` → FastAPI
- Server-only `FASTAPI_BASE_URL`
- Loading / success / validation / not-found / unavailable UI states
- Host-run Next.js; Docker backend unchanged

Learning: [learning/02-nextjs-order-lookup.md](learning/02-nextjs-order-lookup.md)

> Note: Earlier drafts listed Ollama as Phase 1.3. UI-first delivery was Phase 1.3; local classification is **Phase 2.1** (also tracked historically as Phase 1.4).

## Phase 2.1 — Local model setup and validated request classification

| | |
|--|--|
| **Implemented** | Yes |
| **Verified** | Yes (2026-10-21) — mocked pytest; real-model eval 22 cases; live API after Docker Desktop Ollama bind |

Delivered:

- Host Ollama + `qwen3:1.7b` (free quantized weights; Apache-2.0)
- Async Ollama client via `host.docker.internal` (AI not required for `/ready`)
- `POST /api/v1/demo/message-classifications` (classify + extract only)
- Versioned prompt `classification_v1`; schema-constrained JSON + Pydantic validation
- App-enforced human review for `refund_request` / `other`
- Mocked tests + real-model eval report

Learning: [learning/03-local-classification.md](learning/03-local-classification.md) · Host install: [ollama-macos-intel.md](ollama-macos-intel.md)

## Phase 2.2 — Support draft orchestration + Next.js UI

| | |
|--|--|
| **Implemented** | Yes |
| **Verified** | Yes (2026-10-21) — mocked workflow tests; frontend typecheck/build; live smoke when Ollama available |

Delivered:

- `POST /api/v1/demo/support-drafts` (classify → app route → template)
- Deterministic Python templates; model classifies only
- Mandatory `requires_human_review: true` on every workflow response
- Next.js customer-message section + `/api/support-drafts` proxy (90s timeout)
- Injection safety tests (mocked failing classifications); real-model replay recorded honestly

Learning: [learning/04-support-draft-flow.md](learning/04-support-draft-flow.md)

## Phase 2.3 — Grounded local policy retrieval

| | |
|--|--|
| **Implemented** | Yes |
| **Verified** | Yes (2026-10-21) — unit tests; frontend typecheck/build; live proxy; real-model e2e eval |

Delivered:

- Fictional demo policy Markdown under `app/policy_docs/`
- Deterministic keyword/token retrieval (no embeddings)
- `return_policy` drafts cite verbatim sections via `sources`
- Refund requests remain human-review handoffs
- Frontend shows source titles/versions/section IDs/text safely

Learning: [learning/05-policy-retrieval.md](learning/05-policy-retrieval.md)

## Phase 3.1 — Persistent support requests and human review

| | |
|--|--|
| **Implemented** | Yes |
| **Verified** | Yes (2026-10-21) |

Delivered:

- Alembic `20261021_0002` — support requests + append-only review events
- Persist on successful `POST /support-drafts` with Idempotency-Key
- Review list/detail/edit/approve/reject with optimistic concurrency
- Next.js `/requests` and `/requests/[id]` (local single-operator demo)

Learning: [learning/06-persistence-and-review.md](learning/06-persistence-and-review.md)

## Phase 3.2 — MVP acceptance and portfolio preparation

| | |
|--|--|
| **Implemented** | Yes |
| **Verified** | Yes (2026-10-25) locally — see distinctions below |

### Completed and verified (local)

- Playwright browser acceptance against isolated `supportflow-acceptance` stack (`:8010`), fixture inference only
- Real-Ollama browser smoke against development API (`:8000`), fixture off
- Fresh acceptance Compose: migrate, seed, API ready; development volume `supportflow_postgres_data` retained
- Backend `docker compose --profile test run --rm test` → 57 passed (mocked inference)
- Frontend `npm ci`, typecheck, production build
- Portfolio docs: README, architecture, demo walkthrough, acceptance report, learning/07
- Screenshots under `docs/screenshots/` (synthetic data)
- GitHub Actions workflow configured at `.github/workflows/ci.yml`

### Implemented but unverified

- **Remote GitHub Actions** — workflow present; **not claimed passed** until a push/PR runs on GitHub

### Known limitations

- Classification / keyword retrieval can be wrong; human review required
- Prompt injection not solved
- No authentication; no outbound messaging
- Approval records a decision only
- Acceptance fixture markers work only when `APP_ENV` is `test` or `acceptance`

### Future work

- Outbound send after explicit approval
- Auth / multi-operator review
- Embeddings / semantic retrieval (explicitly out of MVP)
- Broader evaluation harness

Learning: [learning/07-mvp-acceptance.md](learning/07-mvp-acceptance.md) · Report: [mvp-acceptance-report.md](mvp-acceptance-report.md)

## Next — Outbound send (after explicit approval)

| | |
|--|--|
| **Status** | **Planned (future work)** |

## Out of plan (MVP)

- Actual refunds, live courier APIs, paid cloud inference
- Automatic external messaging without approval
- Express backend; n8n / Make.com for the initial implementation
- Embeddings / vector search; multi-user authentication
