#!/usr/bin/env bash
# Create .env.acceptance for the isolated acceptance Compose project.
# Refuses to overwrite existing files. Does not touch .env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/.env.acceptance"

if [[ -f "$TARGET" ]]; then
  echo "Refusing to overwrite existing $TARGET"
  exit 1
fi

PASSWORD="$(openssl rand -hex 24)"

cat > "$TARGET" <<EOF
# Acceptance-only Compose env — DO NOT COMMIT
APP_ENV=acceptance
APP_NAME=SupportFlow AI Acceptance
POSTGRES_USER=supportflow_acceptance
POSTGRES_PASSWORD=${PASSWORD}
POSTGRES_DB=supportflow
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://supportflow_acceptance:${PASSWORD}@db:5432/supportflow
INFERENCE_FIXTURE=true
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:1.7b
EOF

chmod 600 "$TARGET"
echo "Wrote $TARGET (secrets not printed)."
