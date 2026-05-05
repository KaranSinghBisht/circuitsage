---
license: gemma
base_model: unsloth/gemma-3-4b-it
library_name: peft
pipeline_tag: text-generation
tags:
  - gemma3
  - unsloth
  - lora
  - electronics
  - education
  - circuit-debugging
datasets:
  - circuitsage-qa
metrics:
  - schema_validity_rate
  - experiment_type_exact_match
  - top_fault_id_match
  - safety_refusal_precision
  - safety_refusal_recall
---

# CircuitSage Gemma LoRA

This is the local model-card artifact for the CircuitSage structured diagnosis adapter. The base model tag is `unsloth/gemma-3-4b-it`, verified on Hugging Face during the E5 hardening step. The trained adapter and GGUF are USER ACTION outputs and may not be present in this repository until a Kaggle or Colab GPU run is completed.

## Intended Use

The model is intended to assist electronics students with low-voltage educational circuit debugging. It should produce structured JSON diagnoses that connect expected behavior, observed evidence, likely faults, safety warnings, and the next useful measurement.

It is not intended for live mains, high-voltage, EV-pack, microwave, CRT, SMPS-primary, capacitor-bank, medical, or industrial safety-critical debugging.

## Base Model

- Base model: `unsloth/gemma-3-4b-it`
- Model family: Gemma 3
- License: Gemma terms
- Local serving target: Ollama tag `circuitsage:latest`

## Training Configuration

The planned LoRA configuration is documented in `train/README.md` and `train/unsloth_lora.ipynb`:

| Setting | Value |
|---|---|
| Quantization/load | 4-bit |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj` |
| Learning rate | `2e-4` |
| Epochs | 3 |
| Max sequence length | 4096 |
| Dataset | `train/dataset/circuitsage_qa.jsonl` |

## Evaluation

Evaluation harness: `train/eval/harness.py`.

Holdout: `train/eval/eval_set.jsonl`, 200 deterministic examples selected by taking every 30th row from the committed dataset.

Current metrics are placeholders because local Ollama was unavailable during hardening. The attempted command failed with connection refused at `http://localhost:11434`:

```bash
backend/.venv/bin/python train/eval/harness.py --model gemma3:4b
```

| Metric | Value |
|---|---:|
| schema_validity_rate | TBD |
| experiment_type_exact_match | TBD |
| top_fault_id_match | TBD |
| safety_refusal_precision | TBD |
| safety_refusal_recall | TBD |
| mean_latency_ms | TBD |

After Ollama is available, run the harness and copy the metrics from `train/eval/last_run.json`.

## Ethical Considerations

CircuitSage should ask for evidence before making strong claims. It must refuse unsafe high-voltage and mains debugging. The deterministic backend safety check remains required even when model output appears safe.

The model can produce plausible but incorrect diagnoses when the topology is unsupported, measurements are mislabeled, or a photo lacks enough context. Production use should keep uncertainty calibration, tool traces, and deterministic fallback visible to the student.

## Limitations

Training data is synthetic and concentrated on educational circuits. The adapter should not be expected to generalize to arbitrary analog, RF, power, or industrial systems. It should not replace instructor supervision, datasheet review, or basic lab safety procedures.

## Reproducibility

1. Validate the dataset with `backend/.venv/bin/python train/dataset/validate.py`.
2. Run `train/unsloth_lora.ipynb` on Kaggle or Colab with a GPU.
3. Export the LoRA and GGUF artifacts into `train/output/`.
4. Create the local Ollama model with `ollama create circuitsage:latest -f train/output/circuitsage.Modelfile`.
5. Run `backend/.venv/bin/python train/eval/harness.py --model circuitsage:latest`.
