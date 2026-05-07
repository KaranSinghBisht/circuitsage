# CircuitSage Eval Kernel (Kaggle T4)

Runs `train/eval/harness.py`-equivalent metrics against `google/gemma-3-4b-it` on a Kaggle T4 GPU. Use this when local Ollama is impractical (RAM-constrained machine).

## What it computes

- `schema_validity_rate` — fraction of outputs that parse as valid JSON with the required schema fields.
- `experiment_type_exact_match` — fraction matching the gold `experiment_type` label.
- `top_fault_id_match` — among rows with a gold top-fault, fraction where the predicted top-fault `id` matches.
- `safety_refusal_precision` / `safety_refusal_recall` — over the 200-row eval set with safety-branch labels.
- `mean_latency_ms` — mean per-example wall-clock latency at greedy decoding.

## Inputs

- Kaggle dataset: `karansinghbisht/circuitsage-faults-v1` (auto-attached via `kernel-metadata.json`). Provides `eval_set.jsonl`.
- Kaggle Secret: **`HF_TOKEN`** — Gemma 3 weights are HF-gated. Without it the model load step fails. Add via Kaggle → Add-ons → Secrets.

## Push

```bash
kaggle kernels push -p train/kaggle_eval
```

The `is_private: false` flag in `kernel-metadata.json` makes the kernel public so judges can click through from the writeup.

## Retrieve metrics

After the kernel finishes:

```bash
kaggle kernels output karansinghbisht/circuitsage-eval -p train/eval/
mv train/eval/last_run.json train/eval/last_run.json
```

The downloaded `last_run.json` matches the schema produced by `train/eval/harness.py` so it drops in with no transformation.

## Expected runtime

- Model load (4-bit nf4): ~2 minutes.
- 200 examples at greedy decoding, max_new_tokens=512: ~10–15 minutes on T4.
- Total: under 20 minutes per run.

## Re-running with the fine-tuned model

Once the LoRA training kernel finally produces `circuitsage-lora-q4_k_m.gguf`, swap the model load cell to load the merged adapter (or the GGUF via llama.cpp on CPU) and re-run. Compare the two `last_run.json` files in the writeup.
