#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] applying alembic migrations..."
alembic upgrade head

echo "[entrypoint] starting server on port ${SERVER_PORT:-5000}..."
exec python app.py
