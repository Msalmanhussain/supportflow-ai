#!/usr/bin/env bash
# Start isolated acceptance API/DB on 127.0.0.1:8010.
# Uses project/volume names that do not touch development data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/Applications/Docker.app/Contents/Resources/bin:${PATH}"

if [[ ! -f .env.acceptance ]]; then
  ./scripts/generate_acceptance_env.sh
fi

COMPOSE=(docker compose -p supportflow-acceptance
  --env-file .env.acceptance
  -f docker-compose.acceptance.yml)

"${COMPOSE[@]}" build api
"${COMPOSE[@]}" up -d db
"${COMPOSE[@]}" --profile tools run --rm migrate
"${COMPOSE[@]}" --profile tools run --rm seed
"${COMPOSE[@]}" up -d api

echo "Acceptance API: http://127.0.0.1:8010"
echo "For Playwright: set frontend FASTAPI_BASE_URL=http://127.0.0.1:8010 and serve on :3010"
