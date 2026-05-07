# CircuitSage Gemma Fine-Tune

This directory contains the Phase 3 fine-tune scaffold for a CircuitSage-specific Gemma adapter.

## Dataset

```bash
python3 train/dataset/build.py
python3 train/dataset/validate.py
```

The committed `train/dataset/circuitsage_qa.jsonl` has 6,000 validated chat examples (4,978 unique prompts after deduplication) using the same structured diagnosis schema as the runtime API.

## Training

Training is a USER ACTION because it needs a Kaggle or Colab GPU session. Codex does not train this locally on a Mac.

Recommended environments:

- Kaggle free T4: upload this repo or mount it as a dataset, enable GPU, then run `train/unsloth_lora.ipynb`.
- Colab Pro A100: clone the repo, install the notebook dependencies, then run all cells.

The notebook pins the base model to `unsloth/gemma-3-4b-it`, uses 4-bit loading, LoRA rank 16, alpha 32, target modules `q_proj`, `k_proj`, `v_proj`, `o_proj`, learning rate `2e-4`, 3 epochs, and max sequence length 4096.

Expected outputs:

- `train/output/circuitsage-lora/`
- `train/output/circuitsage-lora-q4_k_m.gguf`

## Ollama

After downloading the GGUF into `train/output/`, run:

```bash
ollama create circuitsage:latest -f train/output/circuitsage.Modelfile
ollama run circuitsage:latest
```

`scripts/install.sh` also creates `circuitsage:latest` automatically when `train/output/circuitsage-lora-q4_k_m.gguf` exists.
