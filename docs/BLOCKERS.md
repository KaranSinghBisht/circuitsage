# CircuitSage Build Blockers

## Phase 0.1

- The retired Ollama model tag check cannot literally pass while `docs/WINNING_BUILD_PLAN.md` remains tracked, because the plan itself contains that old tag in the rule and acceptance text. Source/config/handoff references were updated; verification should exclude the plan document or relax the check to tracked runtime paths.
- `bash scripts/check_ollama.sh` failed because Ollama is not reachable at `http://localhost:11434` in this environment. The script reports the correct operator action: `ollama pull gemma3:4b`.

## Phase 3.2

- Unsloth training is a USER ACTION requiring a Kaggle or Colab GPU session. The notebook and instructions are present, but local execution on this Mac was intentionally not attempted.
