# CircuitSage: Stack Traces for Circuits

![CircuitSage cover](../media/cover.png)

## Problem

Software students get stack traces. Electronics students get silence. When a circuit fails, the symptom may be a flat oscilloscope trace, a saturated op-amp output, a hot part, or no signal at all. The student then has to connect theory, simulation, breadboard wiring, datasheets, and instrument readings while an instructor is helping ten other people. That moment is where many labs stop being educational and become trial-and-error.

CircuitSage is a local-first Gemma lab partner for low-voltage educational circuits. The goal is not to replace an instructor or automatically "solve" hardware. The goal is to make the debugging process explicit: what evidence exists, what is expected, what was observed, which safety rules apply, and which single measurement should happen next.

## Solution

The demo story is an inverting op-amp amplifier. The simulator expects a gain of about -4.7, but the bench output is stuck near the positive rail. CircuitSage loads the lab manual, netlist, waveform CSV, bench measurements, datasheets, and screenshots into one session. It parses the netlist, computes expected gain, detects waveform saturation, checks safety, retrieves relevant manual snippets, and asks for the missing measurement: the non-inverting input voltage. When the student enters `V_noninv = 2.8 V`, CircuitSage identifies the floating reference input and explains why the gain equation was not the immediate problem.

The product has four main surfaces. Studio is the desktop workspace for artifacts, tool calls, diagnosis, and reports. Bench Mode is the phone-friendly measurement entry flow paired by QR code. Companion is a persistent screen-aware helper for tools such as LTspice, Tinkercad, MATLAB, and oscilloscope screenshots. Educator view aggregates class patterns: repeated faults, safety refusals, unresolved sessions, and stalled measurements.

![Studio screenshot](../media/screenshots/02_studio.png)

The Educator view shows real aggregate behavior across 476 seeded sessions: floating non-inverting input is the top fault (170 occurrences), then wrong capacitor value (55), load resistance too low (54), incorrect base bias (45), and Rg open in non-inverting mode (45).

![Educator dashboard](../media/screenshots/06_educator.png)

## Tracks

For Future of Education, CircuitSage teaches the debugging loop instead of giving a final answer. It asks for the next measurement, shows evidence, and generates a lab report that explains the reasoning trail.

For Digital Equity, the design assumes intermittent internet and crowded labs. The backend has deterministic fallbacks, and the mobile path is designed for on-device Gemma inference. The demo script includes an airplane-mode scene where the phone toggles airplane mode, asks a voice question, and receives a structured local diagnosis. The iOS on-device bundle remains a USER ACTION until the Gemma file is provisioned on a physical device, but the app path and blocker reporting are already wired.

For Safety & Trust, CircuitSage refuses live mains or high-voltage debugging, warns about stored charge, and keeps uncertainty visible. It has a dedicated `/uncertainty` gallery with eight cases where the correct behavior is to ask for more evidence instead of naming a component fault.

![Uncertainty gallery — when CircuitSage says no](../media/screenshots/07_uncertainty.png)

## Architecture

The backend is a FastAPI microserver with SQLite persistence. Sessions store artifacts, measurements, messages, diagnoses, and generated reports. The deterministic tool layer includes netlist parsing, topology detection for 13 circuits, waveform analysis, expected-vs-observed comparison, datasheet lookup, retrieval over textbook/manual content, safety checks, and PDF generation. The agent orchestrator can call tools through a bounded loop when Ollama is available. When Ollama is unavailable, the deterministic diagnosis still returns an honest `gemma_status` rather than pretending a model ran.

The frontend is a Vite/React application with routes for Studio, Bench, Companion, Educator, Faults, and Uncertainty. It supports four locales, accessibility preferences, desktop packaging, and an iOS app shell. The hosted demo mode is read-only except for seeded demo actions so public reviewers can explore without corrupting the environment.

The demo data is also part of the architecture. Thirteen seed endpoints cover the supported topology catalog, and `scripts/demo_seed.py` creates eight classroom sessions with resolved op-amp cases, unresolved RC cases, a divider load fault, a BJT bias fault, and a safety refusal. That makes the app useful on a fresh install: a reviewer can open the Educator dashboard and immediately see real aggregate behavior instead of an empty analytics shell. The same seed data powers the smoke script and video rehearsal, so demo readiness is tested through the product surface rather than a separate mock.

## Multimodal Workflow

CircuitSage accepts manuals, SPICE-style netlists, waveform CSVs, screenshots, breadboard photos, MATLAB scripts, Arduino sketches, and notes. The schematic-to-netlist path uses Gemma vision when available, validates generated SPICE, and returns low confidence if the photo is insufficient. It no longer fabricates an op-amp netlist from hint text. The Companion mode can capture the current screen and analyze the visible workspace, which is the intended "codex pet" experience for LTspice, Tinkercad, MATLAB, and browser-based labs.

Datasheet support is deliberately practical. If a parsed netlist contains model strings such as `2N3904`, `1N4148`, or `TL072`, CircuitSage automatically looks up up to three matching datasheet briefs and feeds compact pin-map, absolute maximum, typical-use, and common-fault context into the diagnosis.

## Fine-Tune And Evaluation

The repository includes a synthetic instruction dataset at `train/dataset/circuitsage_qa.jsonl` with 6,000 structured examples. Validation checks schema shape, topology distribution, duplicate prompts, safety ratio, and negative-evidence ratio. The eval harness in `train/eval/harness.py` creates a deterministic 200-example holdout by taking every 30th dataset row.

Current eval metrics are placeholders because local Ollama was not reachable during the C1 acceptance run on May 6, 2026. The command `backend/.venv/bin/python train/eval/harness.py --model gemma3:4b` failed with connection refused at `localhost:11434`. The harness imports cleanly and the 200-row eval set is committed. Once Ollama is running, the harness records `schema_validity_rate`, `experiment_type_exact_match`, `top_fault_id_match`, `safety_refusal_precision`, `safety_refusal_recall`, and `mean_latency_ms` to `train/eval/last_run.json`.

Placeholder metrics for the submission draft: schema validity TBD, experiment type exact match TBD, top fault id match TBD, safety refusal precision TBD, safety refusal recall TBD, mean latency TBD.

## Reproducibility

The main path is:

```bash
make install
make demo-seed
bash scripts/demo_smoke.sh
make demo
```

`scripts/demo_smoke.sh` starts the backend, hits all 13 topology seed endpoints, verifies the Educator overview, and opens a PDF report. Backend tests cover the topology pack, integration demo flows, uncertainty gallery, hosted demo guards, datasheets, RAG, PDF generation, streaming drift, and the agent loop. CI is configured for backend tests, frontend build, desktop checks, and dataset validation.

## Safety And Uncertainty

Safety is not only a refusal keyword list. The system blocks mains and high-voltage prompts, logs the refusal in the diagnosis, and asks for qualified supervision. It also handles the quieter trust problem: overconfident answers from incomplete evidence. The uncertainty gallery includes an op-amp netlist missing rails, a claimed RC filter with no capacitor, conflicting repeated measurements, a breadboard photo without topology, an unsupported Wien bridge network, and a voltage reading entered in resistance units. In those cases CircuitSage returns `confidence: low` and asks for the missing evidence.

## Limitation

The central limitation is uncertainty calibration. CircuitSage is strongest when topology, expected behavior, and at least one observed node are available. It is intentionally weaker when photos are unlabeled, measurements conflict, units are wrong, or the circuit is outside the catalog. That limitation is also the differentiator: a useful lab partner should know when not to guess. The next iteration should quantify calibration more rigorously with the LoRA eval harness and expand the gallery into a benchmark.

## Future Work

The next build targets real LTspice/MATLAB importers, richer schematic recognition, physical iPhone airplane-mode verification, a published LoRA adapter, and more circuit families. The project also needs a larger real-student dataset so the model learns how beginners describe faults, not only how synthetic prompts describe them.

## Links

Repository: `https://github.com/<org>/circuitsage` (public on submission day)

Demo video: `https://youtu.be/<demo-video-placeholder>`

Kaggle dataset (synthetic Q&A): https://www.kaggle.com/datasets/karansinghbisht/circuitsage-faults-v1

Kaggle training kernel (Unsloth LoRA on Gemma 3 1B): https://www.kaggle.com/code/karansinghbisht/circuitsage-gemma-lora

Hugging Face dataset card and model card: see `train/dataset/card.md` and `train/output/MODEL_CARD.md` (uploaded to Hugging Face on submission day).
