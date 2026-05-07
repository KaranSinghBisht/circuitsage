# CircuitSage Build Blockers

## Phase 0.1

- The retired Ollama model tag check cannot literally pass while `docs/WINNING_BUILD_PLAN.md` remains tracked, because the plan itself contains that old tag in the rule and acceptance text. Source/config/handoff references were updated; verification should exclude the plan document or relax the check to tracked runtime paths.
- `bash scripts/check_ollama.sh` failed because Ollama is not reachable at `http://localhost:11434` in this environment. The script reports the correct operator action: `ollama pull gemma4:e4b`.

## Phase 3.2

- Unsloth training is a USER ACTION requiring a Kaggle or Colab GPU session. The notebook and instructions are present, but local execution on this Mac was intentionally not attempted.

## Phase 3.3

- `circuitsage:latest` could not be verified in Ollama because the trained GGUF is a USER ACTION output and is not present at `train/output/circuitsage-lora-q4_k_m.gguf`.

## Phase 4

- The iOS on-device inference path is wired through `cactus-react-native@1.13.1` with `expo-llm-mediapipe@0.6.0` as a fallback, but the Gemma 4 E2B `.gguf`/`.task` bundle and physical airplane-mode iPhone acceptance test are USER ACTION items. The app reports the local model as not ready until that bundle is provisioned in a development client.

## Phase 5

- iOS voice input/output is wired through `expo-speech-recognition@3.1.3` and `expo-speech@55.0.13`, but physical microphone/TTS acceptance requires a development client on an iPhone. If system STT fails, the app persists the recording as a session `audio` artifact when a LAN session is selected; a bundled Whisper fallback is not present in this repo.

## K1

- Schematic-to-netlist is wired through the Gemma vision endpoint and validates generated SPICE before use. The live acceptance with a hand-drawn schematic photo requires Ollama running with the configured vision model and a real photo; when vision is unavailable, the endpoint returns low confidence with missing evidence instead of fabricating components.

## K10

- Hosted packaging is present (`Dockerfile`, `fly.toml`, `docs/DEPLOYMENT.md`, `scripts/hosted_start.sh`) and hosted-mode guard tests pass locally. Actual Fly deployment is a USER ACTION requiring a Fly account, deploy credentials, and volume creation.
- A local Docker image build was attempted on 2026-05-05, but Docker Desktop/daemon was not running (`Cannot connect to the Docker daemon at unix:///Users/kryptos/.docker/run/docker.sock`; the default context also failed at `unix:///var/run/docker.sock`). Re-run `docker build -t circuitsage-hosted:local .` once the daemon is available.

## Phase 3.5 follow-up pre-flight

- Pre-flight for `docs/PHASE_3_5_FOLLOWUP_AND_HARDENING.md` stopped on 2026-05-06 because `git status` was not clean before Group A. Dirty entries at the gate were `.omc/project-memory.json`, `.omc/state/agent-replay-d79f5ca6-fc55-4d26-867c-7d5bc110f091.jsonl`, `.omc/state/idle-notif-cooldown.json`, `.omc/state/last-tool-error.json`, `.omc/state/mission-state.json`, `.omc/state/subagent-tracking.json`, and untracked `docs/PHASE_3_5_FOLLOWUP_AND_HARDENING.md`. Per Section 0, Group A must not start until the worktree is clean or the user explicitly chooses how to handle these pre-existing files.

## A3 CI validation

- `.github/workflows/ci.yml` was created on 2026-05-06 and parsed locally as YAML with backend, frontend, and dataset jobs. GitHub Actions cannot be run from this local workspace, and `actionlint` is not installed (`command -v actionlint` returned no path), so final CI-green validation remains pending until a branch is pushed.

## C1 eval harness run

- `backend/.venv/bin/python train/eval/harness.py --model gemma3:4b` was attempted on 2026-05-06, but Ollama was not reachable at `http://localhost:11434` (`httpx.ConnectError: [Errno 61] Connection refused`). The 200-row eval set exists and both `python3 -c "import train.eval.harness"` and `backend/.venv/bin/python -c "import train.eval.harness"` pass. Re-run the harness after starting Ollama and pulling `gemma3:4b`.

## F4 live Gemma status color verification

- The chat status chip is implemented and maps `ollama_gemma_agentic` to green `agentic`, `ollama_gemma_single_shot` to yellow `single_shot`, deterministic fallback to blue `deterministic`, and safety refusal to red `safety_refusal`. The frontend build passes. The Ollama-up visual flip could not be exercised on 2026-05-06 because Ollama is not reachable at `http://localhost:11434`; only the deterministic/down path was verified locally.

## Kaggle training kernel (2026-05-06)

- `train/kaggle_kernel/circuitsage_lora.ipynb` was pushed to https://www.kaggle.com/code/karansinghbisht/circuitsage-gemma-lora as kernel versions 1–8 across this session. Errors encountered, in order: (v1) gated `unsloth/gemma-3-4b-it`; (v2) CUDA arch mismatch with bitsandbytes>=0.45 on T4 SM 7.5; (v3-v4) `ModuleNotFoundError: trl`; (v5) `ImportError: unsloth_zoo`; (v6) `ModuleNotFoundError: triton.ops` (latest Triton dropped that submodule); (v7) same; (v8 with pinned `unsloth==2024.12.4` + `triton==2.3.1`) PyTorch 13.0 vs torchvision 12.8 CUDA mismatch from Kaggle's pre-installed torch. The recommended remedy for the Unsloth Prize lane is to start from Unsloth's published Kaggle template (which manages its own torch + CUDA stack) and copy in our `circuitsage_qa.jsonl` plus the LoRA hyperparameters from this notebook. Local LoRA training on this Mac was intentionally not attempted.
- The Kaggle dataset `karansinghbisht/circuitsage-faults-v1` is uploaded but **private** by default. Toggle to public via the Kaggle web UI before submission so judges can click the dataset link in `docs/KAGGLE_WRITEUP_DRAFT.md`. CLI does not currently expose a visibility toggle for an existing dataset.

## Live agent loop on local CPU (2026-05-06)

- `gemma3:4b` and `gemma4:e4b` are both pulled in local Ollama (3.3 GB and 10 GB respectively). `gemma3:4b` rejects the `tools=` parameter with HTTP 400/404; the `OllamaClient.chat` fallback drops `tools` and retries, giving `gemma_status: ollama_gemma_single_shot`. `gemma4:e4b` accepts `tools=` natively but inference on M-series CPU at 68%/32% CPU/GPU split reaches ~5 tokens/sec — a full agent loop times out the 300 s read timeout in two iterations on the op-amp seed. The deterministic fallback path returns the correct top fault `floating_noninv_input` with the full 8-step tool-call timeline, so the demo is honest. Faster live agentic-mode acceptance requires a CUDA host or Apple Silicon Metal-tuned Ollama build.

## Submission week (2026-05-07)

- **Local Ollama declined for RAM**: running `gemma3:4b` and especially `gemma4:e4b` together (~13 GB) hangs the user's Mac. Eval runs are moved off-device to a new Kaggle GPU kernel at `train/kaggle_eval/circuitsage_eval.ipynb`. User runs `kaggle kernels push -p train/kaggle_eval` to publish; the kernel needs Kaggle Secret `HF_TOKEN` (gemma-3 is HF-gated). Output `last_run.json` is downloaded back into the writeup.
- **GitHub push pending workflow scope**: 75 unpushed local commits on `master`; remote `origin` (https://github.com/KaranSinghBisht/circuitsage.git) was created but rejected the push because the OAuth token lacks the `workflow` scope required to upload `.github/workflows/ci.yml`. User must run `gh auth refresh -h github.com -s workflow` (interactive browser flow), then re-run `git push -u origin master`.
- **HuggingFace publication**: dataset card (`train/dataset/DATASET_CARD.md`) and model card (`train/output/MODEL_CARD.md`) are ready. User runs `HF_TOKEN=<token> python scripts/hf_upload_dataset.py` and `HF_TOKEN=<token> python scripts/hf_upload_model.py` to publish to `huggingface.co/karansinghbisht/circuitsage-faults` and `circuitsage-lora`.
- **Release tag**: after the `git push` lands, run `git tag -a v1.0.0-submission -m "Gemma 4 Good Hackathon submission"` and `git push origin v1.0.0-submission`.
