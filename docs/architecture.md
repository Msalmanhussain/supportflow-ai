# Architecture — SupportFlow AI

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 15 (App Router) + TypeScript on the host |
| Backend | Python 3.12 + FastAPI in Docker |
| Database | PostgreSQL 16 in Docker |
| Local AI | Ollama on the Mac host (`qwen3:1.7b`) — **classifies only** |
| Replies | Deterministic Python templates |
| Policy | Keyword/token retrieval over Markdown in `app/policy_docs/` |

**Not used:** Express, n8n/Make, paid cloud inference, embeddings, vector DB, outbound messaging, multi-user auth.

## Request flow (happy path)

1. Browser → Next.js server proxy (`/api/support-drafts`) → FastAPI.
2. FastAPI validates input; requires `Idempotency-Key`.
3. Short DB lookup for idempotency → **close session**.
4. Local model classifies message (or acceptance fixture when gated).
5. Application routes: order lookup / policy retrieval / handoff.
6. Template renders draft; persist request + `created` event.
7. Operator reviews at `/requests/[id]` (edit / approve / reject).

## Trust boundaries

- Classification is **advisory**, never authorization.
- `requires_human_review: true` on every workflow response; `review_status` tracks whether review happened.
- Approval stores `reviewed_text`; **nothing is sent**.
- Keyword retrieval is **not** semantic search.
- Single-operator local demo — **no authenticated reviewer identity**.
- Services bind to loopback (`127.0.0.1`).

## Key directories

| Path | Role |
|------|------|
| `app/api/routes/` | HTTP endpoints |
| `app/services/` | Classification, drafts, policy, persistence |
| `app/policy_docs/` | Fictional demo policies |
| `app/prompts/` | Versioned classification prompt |
| `frontend/src/app/` | Pages + BFF proxies |
| `alembic/versions/` | Schema migrations |

## Environments

| `APP_ENV` | Purpose |
|-----------|---------|
| `development` | Local demo (real Ollama) |
| `test` | Pytest / CI |
| `acceptance` | Isolated browser acceptance (+ optional `INFERENCE_FIXTURE`) |
| `production` | Not used for this portfolio MVP |
