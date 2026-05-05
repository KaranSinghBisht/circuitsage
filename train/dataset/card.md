---
license: mit
language:
  - en
task_categories:
  - text-generation
  - question-answering
size_categories:
  - 1K<n<10K
pretty_name: CircuitSage Structured Diagnosis QA
tags:
  - electronics
  - circuit-debugging
  - education
  - safety
  - gemma
---

# CircuitSage Structured Diagnosis QA

This dataset contains 6,000 synthetic chat examples for low-voltage electronics lab debugging. Each row is a three-message conversation: system instruction, student prompt, and assistant response. The assistant response is JSON using the same structured diagnosis shape as the CircuitSage API.

## Intended Use

Use this dataset to fine-tune or evaluate a model that helps electronics students debug low-voltage educational circuits. The expected behavior is evidence-seeking: identify the topology when possible, compare expected and observed behavior, rank likely faults only when evidence is sufficient, ask for one next measurement, and refuse unsafe high-voltage or mains debugging.

Do not use this dataset as a source of instructions for live mains, high-voltage, EV-pack, microwave, CRT, SMPS-primary, or capacitor-bank debugging.

## Construction

The dataset is generated from local templates in `train/dataset/templates.py` and built with `train/dataset/build.py`. The builder combines:

- topology-specific fault catalogs,
- low-voltage lab setup variables,
- expected behavior text,
- observed symptom variations,
- negative/evidence-missing branches,
- safety-refusal prompts,
- original and rule-based paraphrases.

When Ollama is unavailable, rule-based augmentation keeps the dataset build deterministic and transparent. The validator checks schema shape, prompt duplication, safety ratio, negative branch ratio, topology distribution, and required assistant fields.

## Distribution

Validation command:

```bash
backend/.venv/bin/python train/dataset/validate.py
```

Latest local validation output:

| Split | Count | Ratio |
|---|---:|---:|
| total rows | 6000 | 1.000 |
| unique user prompts | 4978 | 0.830 |
| max prompt duplicates | 4 | n/a |

Topology distribution:

| Topology | Count | Ratio |
|---|---:|---:|
| bjt_common_emitter | 950 | 0.158 |
| full_wave_rectifier | 950 | 0.158 |
| op_amp_inverting | 950 | 0.158 |
| op_amp_noninverting | 950 | 0.158 |
| rc_lowpass | 950 | 0.158 |
| safety_refusal | 300 | 0.050 |
| voltage_divider | 950 | 0.158 |

Branch distribution:

| Branch | Count | Ratio |
|---|---:|---:|
| fault | 5340 | 0.890 |
| negative | 360 | 0.060 |
| safety | 300 | 0.050 |

Paraphrase sources:

| Source | Count | Ratio |
|---|---:|---:|
| original | 1902 | 0.317 |
| rule | 3798 | 0.633 |
| safety_template | 300 | 0.050 |

## Schema

Assistant content is a JSON object with these required keys:

- `experiment_type`
- `expected_behavior`
- `observed_behavior`
- `likely_faults`
- `next_measurement`
- `safety`
- `student_explanation`
- `confidence`

## Licensing

The dataset artifact is intended to be released under MIT. The examples are synthetic and generated from original project templates and local fault catalogs.

## Known Biases

The dataset is synthetic, so it overrepresents cleanly described educational lab faults compared with real student language. Rule-based augmentation can produce repeated phrasing patterns when Ollama is down. The topology coverage is intentionally narrow and does not represent industrial, mains, RF, power electronics, or safety-critical diagnosis.

## Limitations

The dataset should not be treated as a source of electrical safety authority. It is designed to train evidence-seeking behavior for low-voltage educational contexts, not autonomous repair instructions. Real deployment should keep deterministic safety checks and uncertainty handling outside the model.
