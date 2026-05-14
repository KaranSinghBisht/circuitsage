"""Deploy Ollama with gemma3:4b on Modal Labs as a hosted endpoint.

Why this exists: CircuitSage's Companion vision loop needs gemma3:4b, which takes
~5-6 GB RAM at runtime. On an 8 GB Mac the model thrashes swap and inference is
unusable for hotkey UX. Modal gives us a T4 GPU + auto-sleep behind an Ollama-API
endpoint, so the backend code is unchanged — we just point OLLAMA_BASE_URL at it.

ONE-TIME SETUP
==============
1. Install Modal CLI:
       pip install modal
2. Authenticate (opens a browser, free signup):
       modal token new
3. Deploy this app:
       modal deploy scripts/deploy_ollama_modal.py
4. Modal prints a URL like:
       https://<your-handle>--circuitsage-ollama-serve.modal.run
5. Export it for the backend:
       export OLLAMA_BASE_URL="https://<your-handle>--circuitsage-ollama-serve.modal.run"
       export OLLAMA_MODEL="gemma3:4b"
       export OLLAMA_VISION_MODEL="gemma3:4b"
6. Restart the backend. Companion is now hosted.

COST
====
- Free tier: $30/month credit (resets monthly, no card required).
- T4 GPU: ~$0.59/hour active. Container auto-sleeps after 5 min idle.
- Cold start with volume-cached model: ~20-40 s.
- First-ever cold start (downloads the model): ~3-5 min.
- For a one-day demo recording session you'll consume ~$1-2 of credit.

ARCHITECTURE
============
- Modal volume `ollama-models` persists the pulled model across cold starts.
- @modal.web_server exposes Ollama's port 11434 over HTTPS at the Modal URL.
- Idle timeout is 600 s; first request after that triggers a fast cold start.
- No CORS configuration needed — backend → Modal is server-to-server.
"""

from __future__ import annotations

import modal


MODEL_NAME = "gemma3:4b"
APP_NAME = "circuitsage-ollama"
IDLE_TIMEOUT_S = 600
STARTUP_TIMEOUT_S = 300


image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "ca-certificates", "zstd")
    .run_commands(
        # Install Ollama via the upstream installer (handles arch + CUDA detection).
        "curl -fsSL https://ollama.com/install.sh | sh",
    )
)

app = modal.App(APP_NAME, image=image)
ollama_volume = modal.Volume.from_name("circuitsage-ollama-models", create_if_missing=True)


@app.function(
    gpu="T4",
    timeout=3600,
    scaledown_window=IDLE_TIMEOUT_S,
    volumes={"/root/.ollama": ollama_volume},
)
@modal.concurrent(max_inputs=4)
@modal.web_server(port=11434, startup_timeout=STARTUP_TIMEOUT_S)
def serve() -> None:
    """Boot ollama serve on cold start, pull the model if not cached, then block.

    The function exits quickly so @modal.web_server can take over reverse-proxying
    port 11434. The pull is fire-and-forget — first /api/chat call may block until
    the model is loaded into RAM (warm volume) or downloaded (cold volume).
    """
    import os
    import subprocess
    import time
    import urllib.request

    os.environ["OLLAMA_HOST"] = "0.0.0.0:11434"
    os.environ["OLLAMA_KEEP_ALIVE"] = "24h"

    subprocess.Popen(["ollama", "serve"])

    deadline = time.monotonic() + 90
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as response:
                if response.status == 200:
                    print(f"[circuitsage-ollama] daemon up; tags returned 200")
                    break
        except Exception as exc:  # noqa: BLE001 - any error means not ready yet
            last_error = exc
        time.sleep(2)
    else:
        raise RuntimeError(f"ollama daemon did not respond on /api/tags within 90s; last={last_error}")

    print(f"[circuitsage-ollama] starting background pull of {MODEL_NAME}")
    subprocess.Popen(
        ["ollama", "pull", MODEL_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@app.local_entrypoint()
def smoke() -> None:
    """Local smoke test: deploy with `modal deploy scripts/deploy_ollama_modal.py`,
    then run `modal run scripts/deploy_ollama_modal.py::smoke` to verify the
    hosted endpoint responds before pointing OLLAMA_BASE_URL at it.
    """
    import os
    import urllib.request

    base_url = os.environ.get("OLLAMA_BASE_URL")
    if not base_url:
        print("Set OLLAMA_BASE_URL to your Modal endpoint URL first.")
        return
    with urllib.request.urlopen(f"{base_url}/api/tags", timeout=30) as response:
        print(response.status, response.read()[:200])
