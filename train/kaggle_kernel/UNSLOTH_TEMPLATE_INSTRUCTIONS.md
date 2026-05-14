# CircuitSage LoRA on Kaggle — Unsloth Template Recipe

Prior attempts (v1-v8 in `docs/BLOCKERS.md`) failed because we pinned bleeding-edge
unsloth/triton/bitsandbytes against Kaggle's stale torch image. **The fix is to fork
Unsloth's official Kaggle template instead of building our own environment.**

## Step 1 — Fork the Unsloth Gemma 3 template

Open one of these (whichever resolves; URL slugs rotate):

- https://www.kaggle.com/code/danielhanchen/gemma-3-4b-conversational-finetune
- https://www.kaggle.com/code/unslothai/gemma-3-conversational-finetune

If neither resolves, search **"Unsloth Gemma 3 conversational"** in Kaggle Code,
sort by "Most votes", pick the most recent Unsloth-authored notebook.

Click **Copy & Edit** to fork it into your account.

## Step 2 — Add our dataset

In the right rail of the kernel editor, click **+ Add Input** and add the dataset
`karansinghbisht/circuitsage-faults-v1`. Confirm `circuitsage_qa.jsonl` is
visible at `/kaggle/input/circuitsage-faults-v1/circuitsage_qa.jsonl`.

## Step 3 — Replace cells with our sections

Open `train/kaggle_kernel/circuitsage_lora_v9.py`. Each `# ===== SECTION N =====`
maps to one cell of the Unsloth template:

| Template cell | Replace with                          |
| ------------- | ------------------------------------- |
| Install cell  | **DO NOT TOUCH** (Unsloth's pinning)  |
| Imports       | Section 2 from `circuitsage_lora_v9.py` |
| Model load    | Section 3                             |
| Dataset load  | Section 4                             |
| Trainer setup | Section 5                             |
| Save / export | Section 6                             |
| Optional test | Section 7                             |

## Step 4 — Set runtime

Sidebar:

- **Accelerator:** GPU T4 x2 (free tier is enough; Pro tier P100 finishes faster).
- **Internet:** ON (to download the base model + transformers from HF).
- **Persistent storage:** off is fine.

## Step 5 — Save & Run All

Top right → **Save Version** → **Save & Run All**. Expected wall-clock:

- T4 x2: 60-90 min
- P100: 30-45 min

If the run fails with a stack trace mentioning bitsandbytes / triton / torch
version mismatch, **do not edit the install cell**. Instead, re-fork the
Unsloth template (it may have been updated since you forked).

## Step 6 — Download the artifacts

When the run finishes, the **Output** tab shows `/kaggle/working/gguf/`. Download:

- `circuitsage-lora-q4_k_m.gguf` (~2.5 GB)
- `circuitsage.Modelfile`

Place both in `train/output/` of this repo.

## Step 7 — Load into Ollama locally

```bash
cd train/output
ollama create circuitsage:latest -f circuitsage.Modelfile
ollama run circuitsage:latest "what should I check first for a saturated inverting op-amp?"
```

The CircuitSage backend's `_default_ollama_model()` (in `backend/app/config.py`)
auto-detects `circuitsage:latest` and prefers it over `gemma3:4b`. No code change
needed; just restart the backend after `ollama create`.

## Step 8 — Run the eval to confirm it improved

```bash
backend/.venv/bin/python train/eval/harness.py --model circuitsage:latest
```

Compare against the baseline numbers in `train/eval/last_run.json`. Expect:

- `experiment_type_exact_match`: 0.00 → > 0.50 (label conformity is the LoRA's whole job)
- `top_fault_id_match`: 0.00 → > 0.30
- `safety_refusal_recall`: 0.00 → > 0.70 (5% of training data is safety branch)
- `schema_validity_rate`: 0.77 → > 0.90

If the numbers regress: lower learning rate to 1e-4, train for 2 epochs instead
of 3, or hold out 200 rows for early stopping.

## Step 9 — Optional: publish to HF Hub

The repo has `scripts/hf_upload_model.py`. Set `HF_TOKEN` and run it after
`ollama create` succeeds — this satisfies the Unsloth $10K prize requirement
(public adapter + reproducible recipe).
