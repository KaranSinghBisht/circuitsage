# CircuitSage

**Stack traces for circuits.**

CircuitSage is a local-first Gemma lab partner for electronics students. It keeps simulation files, bench evidence, screenshots, measurements, datasheets, tool calls, and reports in one debugging session, then asks for the next useful measurement instead of pretending a circuit fault can be guessed from a vague symptom.

![CircuitSage cover placeholder](media/cover.png)

## Quickstart

```bash
make install && make demo
```

`make demo` starts the FastAPI backend, opens the web app, and runs the Vite dev server. Load the op-amp demo from `/`, open the screen-aware buddy at `/companion`, or seed classroom data with `make demo-seed`.

## What's Inside

- Studio: session workspace for artifacts, measurements, netlist preview, diagnosis, reports, and QR handoff at `/studio/:id`.
- Bench Mode: phone-friendly measurement entry and evidence capture at `/bench/:id`.
- Companion: persistent screen-aware helper for LTspice, Tinkercad, MATLAB, plots, manuals, and screenshots at `/companion`.
- Educator: aggregate dashboard for common faults, safety refusals, unresolved sessions, and stalled measurements at `/educator`.
- Fault Gallery: seeded catalog scenarios for supported circuit faults at `/faults`.
- Uncertainty Gallery: eight low-confidence cases where CircuitSage asks for more evidence at `/uncertainty`.
- PDF reports: generated lab report endpoint at `/api/sessions/:id/report.pdf`.
- Demo seeds: 13 topology seed endpoints under `/api/sessions/seed/:slug`.
- Demo smoke: pre-shoot backend smoke check in [scripts/demo_smoke.sh](scripts/demo_smoke.sh).
- Demo seed data: idempotent educator data seeder in [scripts/demo_seed.py](scripts/demo_seed.py).
- Backend tools: SPICE parsing, topology detection, waveform analysis, safety checks, datasheet lookup, RAG retrieval, and report generation under [backend/app](backend/app).
- macOS app: always-on-top companion shell in [apps/desktop](apps/desktop).
- iOS app: bench-side capture and local-model path in [apps/ios](apps/ios).
- Training scaffold: dataset builder, validation, Unsloth notebook, Ollama Modelfile, and eval harness under [train](train).

## Commands

```bash
make install      # backend venv, npm workspaces, optional Ollama pull
make demo         # backend in background, frontend in foreground
make demo-seed    # idempotently seed educator demo sessions
bash scripts/demo_smoke.sh
make test         # backend pytest, frontend build, desktop check, iOS typecheck
make lint         # ruff when installed, frontend/iOS TypeScript checks
make clean        # remove local env/build artifacts
```

## API Surface

The route map is available at [GET /api/routes](http://localhost:8000/api/routes). It returns every public API endpoint with method, path, and a one-line description.

## Demo Story

The main demo is an inverting op-amp amplifier. The simulator expects gain -4.7, but the bench output is stuck near +12 V. CircuitSage parses the netlist, analyzes the observed waveform, checks safety, retrieves the relevant manual context, asks for `V_noninv`, and identifies the floating reference input after the measurement is entered.

The canonical shot list lives in [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md). The writeup draft lives in [docs/KAGGLE_WRITEUP_DRAFT.md](docs/KAGGLE_WRITEUP_DRAFT.md). The submission checklist lives in [docs/SUBMISSION_CHECKLIST.md](docs/SUBMISSION_CHECKLIST.md).

## Tracks

Future of Education: CircuitSage teaches the debugging loop. Students see expected behavior, observed behavior, evidence gaps, tool calls, and the next measurement instead of only a final answer.

Digital Equity: The app is local-first. Deterministic fallback keeps the workflow usable when Ollama is unavailable, and the iOS path is designed for on-device Gemma use during the airplane-mode demo beat.

Safety & Trust: CircuitSage refuses live mains and high-voltage debugging, warns about stored charge, and keeps uncertainty visible through `/uncertainty` cases where the correct answer is to ask for more evidence.

## Reproducing The LoRA

Start with [train/README.md](train/README.md) for the Unsloth notebook, base model, LoRA hyperparameters, GGUF export path, and Ollama Modelfile.

Validate the dataset:

```bash
backend/.venv/bin/python train/dataset/validate.py
```

Run the eval harness after Ollama is available:

```bash
backend/.venv/bin/python train/eval/harness.py --model gemma3:4b
```

Dataset card placeholder: `train/dataset/card.md` (created in E5).

Model card placeholder: `train/output/MODEL_CARD.md` (created in E5).

## Ollama

```bash
ollama serve
ollama pull gemma4:e4b
export OLLAMA_MODEL=gemma4:e4b
export OLLAMA_BASE_URL=http://localhost:11434
bash scripts/check_ollama.sh
```

If Ollama or the configured model is unavailable, the UI shows an amber Gemma status banner and the backend returns `gemma_status: deterministic_fallback`. Successful model runs report `ollama_gemma_agentic` or `ollama_gemma_single_shot`; malformed model output reports `ollama_partial`.

## Safety Scope

CircuitSage is for low-voltage educational circuits: op-amp labs, RC filters, voltage dividers, transistor amplifiers, 555 timers, MOSFET switches, instrumentation amplifiers, Arduino-style circuits, and signal-generator/oscilloscope exercises.

It refuses detailed live debugging for mains, wall outlets, SMPS primary sides, CRT/flyback circuits, microwave ovens, EV packs, or large capacitor banks.
