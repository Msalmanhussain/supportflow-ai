# MVP acceptance report — Phase 3.2

**Date:** 2026-10-25
**Scope:** Local single-operator portfolio MVP (no outbound send, no auth).

## Criteria vs result

| Criterion | Result | Notes |
|-----------|--------|-------|
| Browser: order-status generate → detail → list → edit → approve | **Executed** | Playwright `chromium-mocked` vs acceptance API `:8010` |
| Browser: reject separate request; terminal read-only | **Executed** | Playwright mocked |
| Browser: unsaved edits block approve | **Executed** | Covered in order-status flow |
| Browser: stale revision (two tabs) | **Executed** | Playwright mocked |
| Browser: policy sources visible | **Executed** | Playwright mocked |
| Browser: needs_information | **Executed** | Playwright mocked |
| Browser: model unavailable error | **Executed** | Fixture marker `ACCEPTANCE_FORCE_OLLAMA_UNAVAILABLE` |
| Browser: narrow viewport | **Executed** | Playwright mocked |
| Real-Ollama browser smoke | **Executed** | 1 passed (~10s) vs development API `:8000`, fixture off |
| Fresh isolated Compose setup | **Executed** | `supportflow-acceptance` + volume `postgres_acceptance_data`; development volume retained |
| Env scripts refuse overwrite | **Executed** | `generate_dev_env.sh` / `generate_acceptance_env.sh` exit 1 when files exist |
| Missing backend surfaces clear error | **Executed** | Proxy `backend_unavailable` when FastAPI unreachable |
| Backend pytest regression | **Executed** | `docker compose --profile test run --rm test` → **57 passed** |
| Frontend typecheck + build | **Executed** | `npm ci`, `npm run typecheck`, `npm run build` |
| GitHub Actions CI | **Configured; remote run not claimed** | `.github/workflows/ci.yml` |
| License selection | **Not done** | Not selected on operator’s behalf |

## Distinctions

- **Mocked browser tests** use `APP_ENV=acceptance` + `INFERENCE_FIXTURE=true` on the acceptance stack only. Development/production ignore the fixture flag.
- **Real-model smoke** is a separate Playwright project (`chromium-real-ollama`) requiring live Ollama and a non-fixture API.
- HTTP-only curls are **not** counted as browser tests.

## Screenshots

Captured under `docs/screenshots/` during mocked Playwright runs (synthetic data only):

- `01-order-status-draft.png`
- `02-request-list-pending.png`
- `03-approved-detail.png`
- `04-policy-sources.png`
- `05-narrow-home.png`

## Secret / artifact audit (proposed tracking)

Ignored (not proposed for commit): `.env`, `.env.acceptance`, `frontend/.env.local`, `frontend/node_modules/`, `frontend/.next/`, Playwright report/result dirs, model weights, DB dumps.

No secrets printed. Trackable tree is application source, docs, lockfiles, and CI config. No license file added.

## Known limitations (accepted)

- Classification and keyword retrieval can be wrong; human review required.
- Prompt injection not solved.
- No authentication / no outbound messaging.
- Approval records a decision only.

## Acceptance verdict

**Local MVP meets its documented acceptance criteria** for Phase 3.2 (browser mocked + real-model smoke + fresh acceptance setup + regressions + portfolio docs). Remote GitHub CI remains unverified until a repository push/PR runs the workflow.
