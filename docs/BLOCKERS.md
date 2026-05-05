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
