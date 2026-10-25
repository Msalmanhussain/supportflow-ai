# SupportFlow AI

Local portfolio MVP for **AI-assisted customer-support triage**: classify a synthetic customer message with a free local model, look up fictional orders / demo policies with application code, draft a reply from **deterministic templates**, and record a **human review decision**. Nothing is sent to a customer.

## Problem and demo workflow

Support teams need help sorting messages (order status, returns, refunds) without trusting a model to authorize actions. This demo shows a safe local pattern:

1. Operator pastes a synthetic customer message (optional email).
2. Local Ollama classifies intent (advisory only).
3. FastAPI routes: verified order lookup, keyword policy retrieval, or human-review handoff.
4. A template produces `draft_text`; the result is persisted as `pending_review`.
5. On `/requests/[id]`, the operator edits, saves, approves, or rejects.
6. Approval stores `reviewed_text`. **Approval records a local review decision. Nothing is sent.**

## Implemented features

- Synthetic order lookup (demo ownership: order ID + email)
- Local classification via Ollama (`qwen3:1.7b`)
- Keyword-grounded fictional policy answers with cited sources
- Persistent support requests + append-only review events
- Next.js UI: generate draft, review queue, detail edit/approve/reject
- Idempotent draft creation; optimistic concurrency on review mutations
- Playwright browser acceptance (mocked inference) + optional real-Ollama smoke
- GitHub Actions CI for backend tests + frontend typecheck/build

## Architecture

See [docs/architecture.md](docs/architecture.md).

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 15 + TypeScript (host) |
| Backend | FastAPI (Docker) |
| DB | PostgreSQL 16 (Docker) |
| AI | Ollama on host — **classifies only** |
| Replies | Deterministic Python templates |
| Policy | Keyword/token matching (not semantic search) |

**Not used:** Express, n8n/Make, paid APIs, embeddings, outbound messaging, multi-user auth.

## Exact setup

Repository root: `supportflow-ai/`

### 1. Environment (never overwrite an existing `.env`)

```bash
./scripts/generate_dev_env.sh   # refuses if .env exists
cp frontend/.env.example frontend/.env.local
# FASTAPI_BASE_URL=http://127.0.0.1:8000
```

### 2. Backend (Docker)

```bash
docker compose build
docker compose up -d db
docker compose --profile tools run --rm migrate
docker compose --profile tools run --rm seed
docker compose up -d api
curl -sS http://127.0.0.1:8000/ready
```

### 3. Ollama (host)

```bash
# Prefer loopback bind — see docs/ollama-macos-intel.md
OLLAMA_HOST=127.0.0.1:11434 ollama serve
ollama pull qwen3:1.7b   # one model only; ~1.4GB
```

### 4. Frontend

```bash
cd frontend
npm ci
npm run typecheck
npm run build
npm run dev
# http://127.0.0.1:3000
```

Missing `FASTAPI_BASE_URL` or a dead backend yields a clear **503** from the Next.js proxy. Missing Ollama yields **503** `ollama_unavailable` on draft generation (`/ready` still works).

### Isolated acceptance stack (does not touch development volumes)

```bash
./scripts/run_acceptance_stack.sh   # project supportflow-acceptance, API :8010
# frontend/.env.local → FASTAPI_BASE_URL=http://127.0.0.1:8010
# PLAYWRIGHT_BASE_URL=http://127.0.0.1:3010 with next start -p 3010
```

## Synthetic example inputs

| Scenario | Message | Email |
|----------|---------|-------|
| Order status | `Where is order SF-1001?` | `alex.rivera@example.com` |
| Needs email | `Where is order SF-1001?` | _(omit)_ |
| Policy | `What is your return window for unused items?` | _(omit)_ |
| Refund handoff | `Please refund my payment for SF-1006.` | _(omit)_ |

## Verification commands

```bash
# Backend unit/integration (mocked Ollama in tests)
docker compose --profile test run --rm test

# Frontend
cd frontend && npm ci && npm run typecheck && npm run build

# Browser acceptance (mocked inference against acceptance API)
# Requires acceptance stack on :8010 and Next on :3010 with matching FASTAPI_BASE_URL
cd frontend && npm run test:e2e

# Optional real-Ollama browser smoke (non-fixture API + live model)
REAL_OLLAMA_SMOKE=1 npm run test:e2e:real-ollama
```

## Honest model / evaluation results

| Eval | Result |
|------|--------|
| Classification (22 cases, `qwen3:1.7b`) | Intent **20/22**; injection cases still fail — see `docs/evaluation/classification_eval_results.md` |
| Policy e2e (16 cases) | Classification **13/16**; retrieval/outcome **15/16** — see `docs/evaluation/policy_eval_results.md` |

**Known failures:** prompt-injection classifications; occasional mis-routes on ambiguous/unsupported topics; keyword retrieval can miss vague questions. Do **not** treat keyword scores as confidence. Prompt injection is **not** solved.

## Scope and safety

- **Local single-operator demo** — no authenticated reviewer identity
- **Approval records a decision; nothing is sent**
- **AI classifies; deterministic templates produce replies**
- **Keyword retrieval is not semantic search**
- Services on loopback; fictional demo policies; simulated tracking only

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/architecture.md](docs/architecture.md) | System design |
| [docs/demo-walkthrough.md](docs/demo-walkthrough.md) | Recording script |
| [docs/mvp-acceptance-report.md](docs/mvp-acceptance-report.md) | Acceptance checklist |
| [docs/learning/07-mvp-acceptance.md](docs/learning/07-mvp-acceptance.md) | Study note |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Phase status |

## Phase status (summary)

| Area | Status |
|------|--------|
| Phases 1.1–3.1 features | **Completed and verified** (see implementation plan) |
| Phase 3.2 browser acceptance / portfolio prep | **Completed and verified** locally; GitHub CI **configured**, remote run not claimed here |
| Outbound send, auth, embeddings | **Future work** |
