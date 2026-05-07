# CircuitSage v1.0.0 — Gemma 4 Good Hackathon Submission

**Tagline:** Stack traces for circuits. An offline-first AI lab partner that helps electronics students debug analog circuits with structured, evidence-seeking diagnoses.

**Submission target:** [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon)
**Tag:** `v1.0.0-submission` (set after final push)
**License:** MIT (code), Gemma terms (model adapter), MIT (synthetic dataset)

---

## What's new in v1.0.0

### Multimodal Gemma agent
- Native function calling on `gemma4:e4b` with a graceful `tools=` fallback for `gemma3:4b`.
- 8-step deterministic tool timeline so the demo is honest even when the live model times out on CPU.
- Vision: schematic → SPICE netlist with confidence + missing-evidence reporting.
- Voice: `expo-speech` (TTS) + `expo-speech-recognition` (STT) on iOS, with audio-artifact persistence as a fallback.

### Topology + fault library
- 13 canonical seed topologies (BJT CE, op-amp inverting/non-inverting, RC LPF, full-wave rectifier, voltage divider, etc.).
- 39 fault entries across the catalog with safety branches.
- Educator dashboard aggregates 476 sessions and ranks 13 fault classes.

### Dataset & training
- 6,000 LoRA fine-tune rows (4,978 unique prompts) under the same structured-diagnosis schema as the runtime API.
- 200-row deterministic eval set (`train/eval/eval_set.jsonl`).
- Eval harness: `train/eval/harness.py` plus a Kaggle T4 mirror in `train/kaggle_eval/circuitsage_eval.ipynb`.

### Apps + hosting
- Web (Vite + React), iOS LAN companion (Expo), desktop (Electron) — all share the same backend contract.
- Hosted parity via `Dockerfile` + `fly.toml`.
- 162 i18n keys × 4 locales (en, es, hi, pt).

### Safety
- Deterministic backend safety check refuses live-mains / high-voltage / capacitor-bank debugging regardless of model output.
- Safety status chip on the chat UI surfaces refusal vs. agentic vs. deterministic-fallback.

---

## How to run

```bash
make install
ollama pull gemma3:4b           # or gemma4:e4b for native tool-calling
make run                         # backend + frontend
```

Smoke test the full demo: `bash scripts/demo_smoke.sh`.

---

## Demo links

- **Kaggle writeup:** https://www.kaggle.com/code/karansinghbisht/circuitsage-writeup
- **Kaggle dataset:** https://www.kaggle.com/datasets/karansinghbisht/circuitsage-faults-v1
- **Kaggle eval kernel:** https://www.kaggle.com/code/karansinghbisht/circuitsage-eval *(metrics source of truth)*
- **Kaggle training kernel:** https://www.kaggle.com/code/karansinghbisht/circuitsage-gemma-lora *(WIP — see Known Limits)*
- **GitHub repo:** https://github.com/KaranSinghBisht/circuitsage *(private until tag)*
- **HuggingFace dataset:** https://huggingface.co/datasets/karansinghbisht/circuitsage-faults *(after upload)*
- **HuggingFace model:** https://huggingface.co/karansinghbisht/circuitsage-lora *(after training + upload)*

---

## Eval metrics

Metrics are produced by `train/kaggle_eval/circuitsage_eval.ipynb` and committed to `train/eval/last_run.json`. Baseline values below are from the 2026-05-07 run on Kaggle T4 (gemma3:4b via Ollama, 200-row holdout). LoRA column fills in once the fine-tuned adapter is published.

| Metric | gemma3:4b (baseline) | circuitsage:latest (LoRA) |
|---|---:|---:|
| `schema_validity_rate` | 0.7700 | TBD |
| `experiment_type_exact_match` | 0.0000 | TBD |
| `top_fault_id_match` | 0.0000 | TBD |
| `safety_refusal_precision` | 0.0000 | TBD |
| `safety_refusal_recall` | 0.0000 | TBD |
| `mean_latency_ms` | 10,801 | TBD |

The base model produces valid JSON 77% of the time but uses human-readable labels (e.g. `"BJT Common Emitter Amplifier Checkout"`) instead of the snake_case ontology our deterministic tools expect (`"bjt_common_emitter"`). It also never matches our safety-refusal pattern. The deterministic safety check in the backend blocks unsafe debugging regardless of model output, so end-user safety doesn't depend on this metric — but the LoRA adapter is what brings label conformity and refusal consistency.

---

## Known limits (USER ACTION items)

1. **LoRA training kernel** still failing dependency hell (8 attempts logged in `docs/BLOCKERS.md`); pivot is to start from Unsloth's official Kaggle template and copy in `circuitsage_qa.jsonl` + the LoRA hyperparameters from `train/unsloth_lora.ipynb`.
2. **iOS physical device test** — Gemma 4 E2B `.gguf`/`.task` bundle and airplane-mode acceptance need a real iPhone + dev client.
3. **Fly.io deploy** — auth + volume creation pending; container is built and `scripts/hosted_start.sh` boots locally.
4. **Demo video** — the `/press` route is wired as B-roll; final reel still to shoot.
5. **Kaggle dataset visibility** — `karansinghbisht/circuitsage-faults-v1` was uploaded private; flip to public via Kaggle UI before the writeup goes live.
6. **HuggingFace publication** — run `scripts/hf_upload_dataset.py` and `scripts/hf_upload_model.py` with an `HF_TOKEN`.
7. **Final GitHub push** — needs `gh auth refresh -h github.com -s workflow` for the OAuth token to gain workflow scope.

---

## Acknowledgements

- Google DeepMind for Gemma 3 and Gemma 4.
- Unsloth for the LoRA tooling.
- The Kaggle Gemma 4 Good Hackathon organizers and judges.

---

**License:** MIT. See `LICENSE` for full text.
