# Fly.io Deploy Runbook — CircuitSage

A self-contained set of commands to take CircuitSage from local repo to a public hosted URL on Fly.io. Run these from the repo root after the GitHub push has landed.

## Prerequisites

- `flyctl` installed: `brew install flyctl` (macOS) or `curl -L https://fly.io/install.sh | sh`.
- Fly account: `fly auth signup` or `fly auth login`.
- Card on file (Fly's free tier covers a single shared-cpu-2x machine + 10 GB volume; CircuitSage fits comfortably).
- Docker daemon running locally (used by `fly deploy` for the build).

## App + volume bootstrap (run once)

```bash
fly auth login

# Create the app named in fly.toml (skip if it already exists)
fly apps create circuitsage-api --org personal

# Create the persistent volume the Dockerfile mounts at /data
fly volumes create circuitsage_data \
  --region bom \
  --size 10 \
  --app circuitsage-api
```

If you want a different region, edit `fly.toml:primary_region` first; popular alternatives are `iad`, `lhr`, `sin`, `nrt`. Pick one near your judges.

## Secrets

The hosted backend reads `OLLAMA_BASE_URL` from `fly.toml`, but if you want to override or add new env vars (e.g. analytics keys, rate-limit overrides), set them as secrets:

```bash
fly secrets set CIRCUITSAGE_HOSTED_RATE_LIMIT_PER_MINUTE=30 --app circuitsage-api
# Add more if needed:
# fly secrets set OPENAI_API_KEY=... --app circuitsage-api
```

## Deploy

```bash
fly deploy --app circuitsage-api --remote-only
```

`--remote-only` builds on Fly's builder so you don't need a local Docker daemon. First deploy takes ~5-10 minutes (image push + cold start).

## Smoke test

```bash
APP_URL=https://circuitsage-api.fly.dev

curl -fsS "$APP_URL/api/health"        # expect {"status":"ok",...}
curl -fsS "$APP_URL/api/seeds"         # expect 13 topology seeds
curl -fsS "$APP_URL/api/educator"      # expect aggregate stats
```

If `/api/health` returns 200 but `/api/seeds` is empty, the SQLite seed didn't run on the volume. Re-run the seed:

```bash
fly ssh console --app circuitsage-api -C "python -m scripts.demo_seed"
```

## Pull Ollama into the volume (optional, real-model demo)

The hosted machine boots without an Ollama model. To run a real model on Fly (slow on shared-cpu-2x — only do this if you've upgraded to a GPU-backed machine):

```bash
fly ssh console --app circuitsage-api
# inside the machine:
ollama pull gemma3:4b
exit
```

Without a pulled model, the backend reports `gemma_status: down` and the deterministic fallback handles diagnoses (still demo-grade).

## Update fly.toml URL in the writeup

Once deployed, replace the placeholder in `docs/KAGGLE_WRITEUP_DRAFT.md` and `docs/RELEASE_NOTES_v1.0.0.md`:

```
hosted demo: https://circuitsage-api.fly.dev
```

Commit + push.

## Logs and rollback

```bash
fly logs --app circuitsage-api          # tail recent
fly status --app circuitsage-api        # machine state, volume, last release
fly releases --app circuitsage-api      # list deploys
fly releases rollback <version>         # roll back to previous deploy
```

## Cost guardrails

- `auto_stop_machines = "stop"` and `min_machines_running = 0` (already set in `fly.toml`) means the machine sleeps when idle and wakes on first request. Cold start is ~5 seconds.
- Single shared-cpu-2x + 10 GB volume = ~$0/month on Fly's free hobby tier (subject to current pricing).
- Disable the app entirely after the hackathon if you don't want it live: `fly apps destroy circuitsage-api`.

## Known limits

- The current `fly.toml` requests 4 GB RAM on shared CPU; that's enough for the FastAPI app + SQLite + Chroma but **not** for running Ollama with `gemma4:e4b` (10 GB). For real-model hosted demos, switch to `performance-4x` + GPU machine, or keep Ollama out of Fly and have the hosted demo proxy to a separate inference URL.
- The volume is `bom` region; cross-region access adds latency. Pick the region nearest your judges via `fly.toml:primary_region` before first `fly volumes create`.
