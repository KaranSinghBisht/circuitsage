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
else
  echo "Ollama not installed. See https://ollama.com/download"
fi

echo "Install complete. Run: make demo"
