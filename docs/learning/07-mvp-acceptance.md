# Learning note — Phase 3.2 MVP acceptance

Study this for the final code walkthrough.

## Final operator flow

1. Generate draft on `/` (message + optional email).
2. Follow **Open in review queue** → `/requests/[id]`.
3. Find the item under `/requests` with status filters.
4. Edit → Save → Approve (or Reject). Unsaved edits disable Approve; terminal states are read-only.
5. Approval stores `reviewed_text`. Nothing is sent.

## How verification is split

| Mode | Stack | Inference |
|------|-------|-----------|
| Mocked browser e2e | `supportflow-acceptance` API `:8010` | `INFERENCE_FIXTURE` markers |
| Real-Ollama smoke | development API `:8000` | Live `qwen3:1.7b` |
| Pytest / CI | `supportflow_test` DB | Mocked / fixture; no Ollama |

Fixture markers live in `app/services/inference_fixture.py` and are honored only when `Settings.allows_inference_fixture` is true (`APP_ENV` in `{test, acceptance}` **and** `INFERENCE_FIXTURE=true`).

## Relevant files

| Area | Paths |
|------|--------|
| Draft UI | `frontend/src/components/SupportDraftForm.tsx` |
| Review UI | `frontend/src/app/requests/page.tsx`, `frontend/src/app/requests/[id]/page.tsx` |
| Proxies / cache | `frontend/src/app/api/**`, `frontend/src/lib/proxy.ts`, `app/main.py` (`Cache-Control: no-store`) |
| Persist/review | `app/services/support_request_persistence.py`, `app/api/routes/support_*.py` |
| Classify / fixture | `app/services/classification.py`, `app/services/inference_fixture.py`, `app/config.py` |
| Policy | `app/policy_docs/`, `app/services/policy_retrieval.py` |
| Browser tests | `frontend/e2e/acceptance.mocked.spec.ts`, `frontend/e2e/acceptance.real-ollama.spec.ts`, `frontend/playwright.config.ts` |
| Acceptance stack | `docker-compose.acceptance.yml`, `scripts/run_acceptance_stack.sh`, `scripts/generate_acceptance_env.sh` |
| CI | `.github/workflows/ci.yml` |
| Report / screenshots | `docs/mvp-acceptance-report.md`, `docs/screenshots/` |

## Commands to re-run

```bash
./scripts/run_acceptance_stack.sh
cd frontend && FASTAPI_BASE_URL=http://127.0.0.1:8010 npm run build && FASTAPI_BASE_URL=http://127.0.0.1:8010 npx next start -p 3010
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3010 npm run test:e2e
# Separate: development API + Ollama, then:
REAL_OLLAMA_SMOKE=1 npm run test:e2e:real-ollama
docker compose --profile test run --rm test
```

## Portfolio honesty

AI classifies; templates write replies; keyword retrieval ≠ semantic search; approval ≠ send; single-operator local demo without auth.
