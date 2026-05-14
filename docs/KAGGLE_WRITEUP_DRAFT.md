# CircuitSage: Stack Traces for Circuits

![CircuitSage cover](../media/cover.png)

## Problem

Software students get stack traces. Electronics students get silence. When a circuit fails the symptom is a flat scope, a saturated output, a hot part, or no signal — and the student has to connect theory, simulation, breadboard wiring, datasheets, and instrument readings while one TA helps ten other people. That moment is where labs stop being educational and become trial-and-error.

CircuitSage is built for a specific user: a second- or third-year EE undergrad at a university without paid Multisim or PSpice tutors, debugging a low-voltage exercise in LTspice, Tinkercad, or MATLAB on a shared lab laptop with intermittent internet, no cloud LLM, no API budget, and a 90-minute lab block. It runs locally and watches their workspace. It does not replace an instructor or automatically solve hardware — it makes the debugging process explicit: what evidence exists, what is expected, what was observed, which safety rules apply, and which single measurement should happen next.

## Solution

Demo story: an inverting op-amp amplifier. Simulator expects gain ≈ −4.7; bench output is stuck near the positive rail. CircuitSage parses the netlist, computes expected gain, detects waveform saturation, checks safety, retrieves manual snippets, and asks for the missing measurement: the non-inverting input voltage. When the student enters `V_noninv = 2.8 V`, CircuitSage identifies the floating reference input and explains why the gain equation was not the immediate problem.

Four surfaces: **Studio** (artifacts, tool calls, diagnosis, reports), **Bench Mode** (phone-friendly entry via QR), **Companion** (screen-aware hotkey helper for LTspice/Tinkercad/MATLAB), **Educator** (class-wide aggregates over 476 seeded sessions; top fault: floating non-inverting input, 170×).

![Studio screenshot](../media/screenshots/02_studio.png)
![Educator dashboard](../media/screenshots/06_educator.png)

## Tracks

**Future of Education** — teaches the debugging loop instead of giving a final answer: next measurement, evidence trail, post-lab report.

**Digital Equity** — assumes intermittent internet and crowded labs. Backend has deterministic fallbacks; mobile path runs Gemma on-device. Airplane-mode demo beat is wired (iOS Gemma bundle is a USER ACTION until provisioned on a physical device).

**Safety & Trust** — refuses live mains and high-voltage, warns about stored charge, keeps uncertainty visible. The `/uncertainty` gallery shows eight cases where the correct answer is to ask for more evidence instead of naming a fault.

![Uncertainty gallery — when CircuitSage says no](../media/screenshots/07_uncertainty.png)

## Architecture

A FastAPI microserver with SQLite persistence stores artifacts, measurements, messages, diagnoses, and reports. The deterministic tool layer covers netlist parsing, topology detection for 13 circuits, waveform analysis, expected-vs-observed comparison, datasheet lookup, RAG retrieval over manual content, safety checks, and PDF generation. The agent orchestrator runs a bounded tool loop when Ollama is reachable; otherwise the deterministic diagnosis still returns an honest `gemma_status` rather than pretending a model ran.

The frontend is a Vite/React app with routes for Studio, Bench, Companion, Educator, Faults, and Uncertainty — four locales, accessibility preferences, desktop packaging, and an iOS app shell. Hosted demo mode is read-only except for seeded actions.

`scripts/demo_seed.py` creates eight classroom sessions across the topology catalog so a reviewer opening Educator on a fresh install sees real aggregates immediately, not an empty shell. The same seed data drives the smoke script and video rehearsal — demo readiness is tested through the product surface, not a separate mock.

## Companion: Click-to-Act on a Live LTspice Window

`Cmd+Shift+Space` inside LTspice → one Gemma vision call sees the schematic and returns structured JSON: detected topology, visible components, suspected faults, suggested deterministic tools to run. The orchestrator runs those tools immediately — `score_faults` against the topology catalog, `lookup_datasheet` for any visible op-amp/BJT, `retrieve_rag` for textbook excerpts — and renders each result inline as a click-to-act button. Click "Look up TL081 datasheet" → pin map + common faults inline. Click "Capture again after grounding V+" → re-runs the loop after the fix. Each turn appends to a persistent companion session so the second ask carries the first screenshot and answer into the prompt.

`Cmd+Shift+X` drops a crosshair: paint just the region you care about (one bulb, one waveform trace, one error message). Only the crop goes to the vision encoder — dramatically better recognition than a full-screen capture, which Gemma 3 4B's vision encoder degrades on at the tight pixel density of a real schematic.

A desktop "pet" — stylized DIP chip with two LED eyes — sits in the corner and mirrors the Companion's state visually: blue eyes while a vision call is in flight, green bounce on a high-confidence diagnosis, yellow squint on low, red on a safety refusal. Click to open the companion, double-click to start a highlight. It's the only signal the student needs when CircuitSage is otherwise out of sight in the menu bar.

Students aren't in a chat tab — they're in their simulator. CircuitSage joins them there. No competing entry we found integrates with a desktop EDA tool.

## Multimodal Workflow

CircuitSage accepts manuals, SPICE-style netlists, waveform CSVs, screenshots, breadboard photos, MATLAB scripts, Arduino sketches, and notes. The schematic-to-netlist path uses Gemma 4 vision when available, validates generated SPICE, and returns low confidence if the photo is insufficient. It does not fabricate an op-amp netlist from hint text.

Datasheet support is deliberately practical. If a parsed netlist contains model strings such as `2N3904`, `1N4148`, or `TL072`, CircuitSage automatically looks up up to three matching datasheet briefs and feeds compact pin-map, absolute maximum, typical-use, and common-fault context into the diagnosis.

## Why Gemma 4 Specifically

- **Native multimodal vision on a 4B model.** The Companion needs a model small enough for a student laptop yet vision-capable enough to read an LTspice canvas, breadboard photo, or scope screenshot. `gemma3:4b` today (~3.3 GB disk, ~5 GB RAM); `gemma4:e4b` is the upgrade path — one `OLLAMA_VISION_MODEL` env var swap. Both Apache-2.0, both run on the same backend code.
- **Function calling + structured JSON.** Companion returns a typed JSON object (`detected_topology`, `detected_components`, `detected_measurements`, `suspected_faults`, `suggested_actions`) in one vision call; the orchestrator chains `score_faults`, `lookup_datasheet`, `retrieve_rag` deterministically. Studio uses Ollama's native `tools=` when the model accepts it (Gemma 4 E4B); when it doesn't (Gemma 3 4B), prompt-driven structured output produces an identical API contract.
- **128K context.** A short datasheet + full session transcript in one call.
- **Apache 2.0.** No tokens, no telemetry, no rate limits — critical for the named user.
- **Local inference via Ollama.** Single binary, runs on a 2024 MacBook or classroom Raspberry Pi 5. For laptops below 16 GB the same backend points at a **Modal-hosted Ollama** via one `OLLAMA_BASE_URL` swap ([docs/HOSTED_OLLAMA_MODAL.md](../docs/HOSTED_OLLAMA_MODAL.md)) — local-first architecture, GPU rented by the hour only when needed.

Cloud APIs defeat the offline narrative. Smaller models can't read the schematic. Larger models can't run on the laptop. The Gemma family is the only size-and-license sweet spot for this user.

## Fine-Tune And Evaluation

The repository includes a synthetic instruction dataset at `train/dataset/circuitsage_qa.jsonl` with 6,000 structured examples. Validation checks schema shape, topology distribution, duplicate prompts, safety ratio, and negative-evidence ratio. The eval harness in `train/eval/harness.py` creates a deterministic 200-example holdout by taking every 30th dataset row.

Live metrics come from the public Kaggle kernel `karansinghbisht/circuitsage-eval`. It installs Ollama on a Kaggle T4 worker, pulls `gemma3:4b`, and runs the harness over all 200 rows of `eval_set.jsonl` from the `karansinghbisht/circuitsage-faults-v1` dataset, writing `last_run.json` with schema validity, experiment-type match, top-fault-id match, safety refusal precision/recall, and mean latency. Reproducible by any Kaggle account; no local GPU needed.

**Baseline numbers from the eval kernel (gemma3:4b on Kaggle T4, run 2026-05-07T10:00 UTC, see `train/eval/last_run.json`):**

| Metric | gemma3:4b (base) |
|---|---:|
| schema_validity_rate | 0.7700 (154 / 200) |
| experiment_type_exact_match | 0.0000 |
| top_fault_id_match | 0.0000 (177 fault rows) |
| safety_refusal_precision | 0.0000 |
| safety_refusal_recall | 0.0000 (14 / 200 gold-refuse) |
| mean_latency_ms | 10,801 |

**Honest interpretation.** The base model produces valid JSON 77% of the time, but its `experiment_type` and `fault_id` strings are human-readable rather than the snake_case ontology our deterministic tools expect (e.g. `predicted="BJT Common Emitter Amplifier Checkout"` vs `gold="bjt_common_emitter"`). The semantics are often correct; the labels are not. The base model also never refuses any of the 14 high-voltage safety prompts. This is exactly the gap the Unsloth LoRA targets — label conformity and consistent refusals. The backend's deterministic `safety_check` blocks unsafe debugging regardless of model output, so end-user safety does not depend on the model's recall here; the eval just makes the gap visible.

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

The central limitation is uncertainty calibration. CircuitSage is strongest with topology + expected behavior + at least one observed node; intentionally weaker on unlabeled photos, conflicting measurements, wrong units, or out-of-catalog circuits. That limit is also the differentiator — a useful lab partner should know when not to guess. The base vision encoder also struggles with breadboard photos at full resolution, which is why the highlight crop is the recommended interaction for novel circuits.

## Future Work

Real LTspice/MATLAB importers, richer schematic recognition, physical iPhone airplane-mode verification, a published LoRA adapter, more circuit families, and a real-student dataset so the model learns how beginners describe faults.

## Links

Repository: https://github.com/KaranSinghBisht/circuitsage

Demo video: linked here on submission day; the `/press` route in the app is wired as B-roll.

Kaggle dataset (synthetic Q&A): https://www.kaggle.com/datasets/karansinghbisht/circuitsage-faults-v1

Kaggle eval kernel (Gemma 3 4B via Ollama on T4): https://www.kaggle.com/code/karansinghbisht/circuitsage-eval

Kaggle training kernel (Unsloth LoRA on Gemma 3 1B): https://www.kaggle.com/code/karansinghbisht/circuitsage-gemma-lora

Hugging Face dataset card and model card: ship in-repo at `train/dataset/card.md` and `train/output/MODEL_CARD.md`. Hub upload via `scripts/hf_upload_dataset.py` once the LoRA GGUF lands from the Kaggle Unsloth run.
