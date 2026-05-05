#!/usr/bin/env bash
set -euo pipefail

python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt

npm install
npm --prefix frontend install
npm --prefix apps/desktop install
npm --prefix apps/ios install || true

if command -v ollama >/dev/null 2>&1; then
  ollama pull "${OLLAMA_MODEL:-gemma3:4b}"
  ollama pull "${OLLAMA_EMBED_MODEL:-nomic-embed-text}"
  if [ -f train/output/circuitsage-lora-q4_k_m.gguf ]; then
    ollama create circuitsage:latest -f train/output/circuitsage.Modelfile
  fi
else
  echo "Ollama not installed. See https://ollama.com/download"
fi

echo "Install complete. Run: make demo"
