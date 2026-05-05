#!/usr/bin/env bash
set -euo pipefail

base="${OLLAMA_BASE_URL:-http://localhost:11434}"
model="${OLLAMA_MODEL:-gemma3:4b}"
echo "Ollama base: $base"
echo "Model: $model"
curl -sf "$base/api/tags" >/dev/null || { echo "Ollama not reachable"; exit 1; }
curl -sf "$base/api/show" -d "{\"name\":\"$model\"}" >/dev/null || {
  echo "Model $model not loaded. Run: ollama pull $model"; exit 1;
}
echo "Ollama OK"
