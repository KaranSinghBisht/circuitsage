#!/usr/bin/env bash
set -euo pipefail

mkdir -p "${CIRCUITSAGE_UPLOAD_DIR:-/data/uploads}" "$(dirname "${CIRCUITSAGE_DATABASE_PATH:-/data/circuitsage.db}")" "${OLLAMA_MODELS:-/data/ollama}"

if command -v ollama >/dev/null 2>&1; then
  ollama serve >/tmp/circuitsage-ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    if curl -fsS "${OLLAMA_BASE_URL:-http://127.0.0.1:11434}/api/tags" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if [ "${CIRCUITSAGE_PULL_MODEL:-1}" = "1" ]; then
    ollama pull "${OLLAMA_MODEL:-gemma4:e4b}" >/tmp/circuitsage-ollama-pull.log 2>&1 || true
  fi
else
  echo "ollama binary not present; hosted demo will use deterministic fallback until an Ollama sidecar is attached." >&2
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
