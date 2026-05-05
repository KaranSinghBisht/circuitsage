# CircuitSage Dataset

`build.py` generates synthetic circuit-fault chat examples from the runtime fault catalog in `backend/app/services/fault_data/*.json`, plus safety refusal examples.

Procedure:

1. Load each topology and fault.
2. Fill templated student questions with different symptom, measurement, and wording variants.
3. Emit assistant responses as the same structured JSON schema used by the backend diagnosis endpoint.
4. Add high-voltage/mains refusal examples as about 5 percent of the dataset.
5. Run `validate.py` before training.

Local augmentation hook:

```bash
python3 train/dataset/augment.py --in seeds.jsonl --out augmented.jsonl --variants 5
```

The augmenter is optional and intentionally refuses to invent labels; it only rewrites the user question when a local Ollama model is available.
