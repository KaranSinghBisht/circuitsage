# CircuitSage Eval Harness

This directory contains the local LoRA evaluation harness for the Unsloth/Gemma submission.

## Holdout Set

`eval_set.jsonl` is deterministic: it takes every 30th row from `train/dataset/circuitsage_qa.jsonl`, using the committed dataset order. With the current 6,000-row dataset, that produces exactly 200 held-out examples.

Regenerate only after intentionally rebuilding the dataset:

```bash
python3 - <<'PY'
from pathlib import Path
src = Path("train/dataset/circuitsage_qa.jsonl")
dst = Path("train/eval/eval_set.jsonl")
selected = [line for index, line in enumerate(src.read_text().splitlines(), start=1) if index % 30 == 0]
dst.write_text("\n".join(selected) + "\n")
print(len(selected))
PY
```

## Running

Start Ollama and make sure the model tag exists:

```bash
ollama pull gemma3:4b
python train/eval/harness.py --model gemma3:4b
```

For a locally built CircuitSage adapter:

```bash
ollama create circuitsage:latest -f train/output/circuitsage.Modelfile
python train/eval/harness.py --model circuitsage:latest
```

Set `OLLAMA_BASE_URL` or pass `--base-url` when Ollama is not on `http://localhost:11434`.

## Metrics

The harness writes timestamped results to `train/eval/runs/` and mirrors the latest run to `train/eval/last_run.json`.

- `schema_validity_rate`: model output parses as JSON and matches the structured diagnosis contract.
- `experiment_type_exact_match`: predicted topology equals the gold topology.
- `top_fault_id_match`: predicted first fault id equals the gold first fault id when the gold answer has one.
- `safety_refusal_precision`: predicted safety refusals that are truly safety examples.
- `safety_refusal_recall`: gold safety examples that the model refuses.
- `mean_latency_ms`: average `/api/chat` latency across the run.

If Ollama is down in CI or on a laptop, validate syntax with:

```bash
python -c "import train.eval.harness"
```
