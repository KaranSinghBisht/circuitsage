# CircuitSage Build Blockers

## Phase 0.1

- The retired Ollama model tag check cannot literally pass while `docs/WINNING_BUILD_PLAN.md` remains tracked, because the plan itself contains that old tag in the rule and acceptance text. Source/config/handoff references were updated; verification should exclude the plan document or relax the check to tracked runtime paths.
- `bash scripts/check_ollama.sh` failed because Ollama is not reachable at `http://localhost:11434` in this environment. The script reports the correct operator action: `ollama pull gemma3:4b`.

## Phase 3.2

- Unsloth training is a USER ACTION requiring a Kaggle or Colab GPU session. The notebook and instructions are present, but local execution on this Mac was intentionally not attempted.

## Phase 3.3

- `circuitsage:latest` could not be verified in Ollama because the trained GGUF is a USER ACTION output and is not present at `train/output/circuitsage-lora-q4_k_m.gguf`.

## Phase 4

- The iOS on-device inference path is wired through `cactus-react-native@1.13.1` with `expo-llm-mediapipe@0.6.0` as a fallback, but the Gemma 4 E2B `.gguf`/`.task` bundle and physical airplane-mode iPhone acceptance test are USER ACTION items. The app reports the local model as not ready until that bundle is provisioned in a development client.
