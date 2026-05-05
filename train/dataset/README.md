# CircuitSage Dataset

`build.py` generates synthetic circuit-fault chat examples from the runtime fault catalog in `backend/app/services/fault_data/*.json`, plus negative-evidence and safety refusal examples.

Procedure:

1. Load each topology and fault.
2. Render the per-topology template library in `templates.py` with deterministic numeric fillers, personas, and question styles.
3. Ask Ollama/Gemma for paraphrases when available.
4. If Ollama is down, use the rule-based fallback and mark rows with `meta.paraphrase_source = "rule"`.
5. Emit assistant responses as the same structured JSON schema used by the backend diagnosis endpoint.
6. Add negative-evidence examples and high-voltage/mains refusal examples.
7. Run `validate.py` before training.

Local augmentation hook:

```bash
python3 train/dataset/augment.py --in seeds.jsonl --out augmented.jsonl --variants 5
```

If the validator reports mostly `rule` paraphrases, re-run with Ollama and `gemma3:4b` loaded before final training. Rule-based examples are acceptable for CI but should be filtered or regenerated for the highest-quality LoRA run.
