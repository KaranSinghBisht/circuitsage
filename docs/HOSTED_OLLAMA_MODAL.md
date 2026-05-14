# Hosted Ollama via Modal Labs

Your 8 GB Mac cannot comfortably host `gemma3:4b` for the Companion vision loop.
This doc gets you a hosted Ollama endpoint in ~10 minutes with $30/month of
free credit (resets monthly, no card required) so the backend can stay unchanged
— just point `OLLAMA_BASE_URL` at Modal.

## First: try local once (it might surprise you)

Run this before committing to the hosted path. Some 8 GB Macs can squeeze `gemma3:4b` in if nothing else is open:

```bash
ollama pull gemma3:4b
time ollama run gemma3:4b "Reply with just OK"
```

- If it prints OK in under 20 seconds: skip this whole doc. Use local.
- If it OOMs / takes minutes / hangs your Mac: continue below.

## Step 1 — Install Modal CLI

```bash
pip install modal
modal token new   # opens a browser; free signup, no card
```

## Step 2 — Deploy

```bash
modal deploy scripts/deploy_ollama_modal.py
```

Modal prints something like:

```
✓ Created web endpoint
  https://karanbisht--circuitsage-ollama-serve.modal.run
```

That URL is your new `OLLAMA_BASE_URL`. Save it.

## Step 3 — Point the backend at Modal

Either edit `.env` (create from `.env.example` if needed) or export inline:

```bash
export OLLAMA_BASE_URL="https://YOURHANDLE--circuitsage-ollama-serve.modal.run"
export OLLAMA_MODEL="gemma3:4b"
export OLLAMA_VISION_MODEL="gemma3:4b"
make demo
```

The backend's `OllamaClient` already speaks the Ollama HTTP API; nothing else changes.

## Step 4 — First-call cold start

First-ever call to `/api/companion/analyze` will trigger:
1. Modal cold-start (~10 s)
2. Ollama daemon boot inside the container (~5 s)
3. **Model pull** — only on the very first deploy, ~3-5 minutes (gemma3:4b is 3.3 GB)

After the first pull, the model lives on a Modal volume. Subsequent cold starts skip the pull and take ~20-40 s. Active inference: ~3-5 s per Companion call on T4 GPU.

## Step 5 — Verify

```bash
curl https://YOURHANDLE--circuitsage-ollama-serve.modal.run/api/tags
```

Should return `{"models":[{"name":"gemma3:4b",...}]}`.

Then in CircuitSage:
1. Open `/companion`.
2. Share your LTspice window.
3. Ask "Why is the output saturating?"
4. Look at the response header — it should read `ollama_gemma_vision · medium confidence · 4520 ms` (the duration_ms field). If it says `deterministic_fallback`, Modal isn't reachable; check the URL and `modal app list`.

## Cost rundown

| Usage | T4 cost | Notes |
| --- | --- | --- |
| Idle (no traffic, sleeping) | $0 | Auto-sleeps after 5 min idle |
| Active (warm) | $0.59/hour | Each Companion call = ~5 s warm time |
| 100 Companion calls/day | ~$0.10/day | Most of the time is sleeping |
| Demo recording (1 hour active) | ~$0.60 | Well under the $30 monthly free |

## Disclosure for the writeup

Since the local-first architecture *can* run on a sufficient machine but your
demo machine doesn't have the RAM, the writeup should note:

> *CircuitSage runs locally on any laptop with ≥ 16 GB RAM via Ollama. For
> the recorded demo, the same backend code points at a hosted Ollama
> instance on Modal Labs — no API change, just `OLLAMA_BASE_URL`. Classroom
> microservers (a Mini PC or Raspberry Pi 5 with 16 GB) replicate the
> deployment for shared school use without any cloud dependency.*

This stays honest with judges while preserving the local-first claim. LENTERA
(prior Gemma 3n winner) used the same framing: *"runs offline on a Raspberry Pi
in the classroom; we recorded the demo on a laptop pointing at the same code."*

## Teardown

```bash
modal app stop circuitsage-ollama   # stop and free the volume
# or just leave it; idle costs are zero
```
