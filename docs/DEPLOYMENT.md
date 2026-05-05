# CircuitSage Hosted Demo

The hosted demo is for judges to click through the Studio flow. It is not the preferred lab setup. Bench Mode and Companion Mode need local LAN, camera, screen-recording, and native permissions, so hosted mode disables those surfaces.

## Container

The root `Dockerfile` builds the Vite frontend, serves `frontend/dist` from FastAPI, installs backend dependencies, and starts `scripts/hosted_start.sh`.

Hosted mode sets:

```bash
CIRCUITSAGE_HOSTED=1
CIRCUITSAGE_HOSTED_RATE_LIMIT_PER_MINUTE=30
CIRCUITSAGE_DATABASE_PATH=/data/circuitsage.db
CIRCUITSAGE_UPLOAD_DIR=/data/uploads
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e4b
OLLAMA_VISION_MODEL=gemma4:e4b
OLLAMA_MODELS=/data/ollama
```

`hosted_start.sh` starts `ollama serve` when the binary is present, then pulls `OLLAMA_MODEL` unless `CIRCUITSAGE_PULL_MODEL=0`. If Ollama is not available or the model cannot be pulled, the API remains usable with deterministic fallback and clearly reports that status.

## Fly.io

USER ACTION: create the Fly app, volume, and deploy credentials.

```bash
fly apps create circuitsage-api
fly volumes create circuitsage_data --size 10 --region bom
fly deploy
fly open
```

Smoke check after deploy:

```bash
curl -s https://circuitsage-api.fly.dev/api/health
curl -s -X POST https://circuitsage-api.fly.dev/api/sessions/seed/op-amp | jq '.seed_diagnosis.gemma_status'
```

The Fly config mounts `/data` for the SQLite DB, uploads, and Ollama model cache.

## Static Frontend Alternative

For Vercel or Cloudflare Pages, build only the frontend and point it at the API:

```bash
VITE_API_BASE=https://circuitsage-api.fly.dev npm --prefix frontend run build
```

Upload `frontend/dist`. The single-container Fly image already serves the same compiled frontend, so this is optional.

## Hosted Guardrails

When `CIRCUITSAGE_HOSTED=1`:

- `/api/companion/*` is disabled because it needs local screen/camera/native permissions.
- `/api/sessions/*/bench/*` is disabled because QR pairing assumes local LAN.
- arbitrary public writes such as session creation, deletion, patching, and artifact upload are blocked.
- seed, diagnose, chat, measurement, report, and schematic-recognition demo actions are rate-limited per IP.

The expected judge path is: open the URL, seed the op-amp demo, inspect the diagnosis/tool trace, and optionally export the PDF report.
