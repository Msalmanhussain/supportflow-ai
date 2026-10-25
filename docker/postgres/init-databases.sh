#!/bin/bash
# Runs only on first PostgreSQL data-directory initialization.
# Creates an isolated test database alongside the development database.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE supportflow_test'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'supportflow_test')\gexec
EOSQL
