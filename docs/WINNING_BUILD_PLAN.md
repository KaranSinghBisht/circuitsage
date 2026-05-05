# CircuitSage — Winning Build Plan

**Audience:** an autonomous coding agent (Codex via `/goal`).
**Goal:** transform CircuitSage from a one-circuit demo into a credible top-tier submission for the Gemma 4 Good Hackathon, deadline **2026-05-18**.
**Today:** 2026-05-05 (13 days remain).
**Repo root:** `/Users/kryptos/Desktop/Projects/gemma/`.

This document is the source of truth for the run. Read it linearly. Execute in order. Do not skip phases.

---

## 0. How to read and execute this doc

Rules for the autonomous run:

1. **Phases are ordered.** Finish Phase 0 acceptance before starting Phase 1. A partial Phase 1 with Phase 0 still broken is worse than Phase 0 alone.
2. **Each task ends with `Acceptance`.** Do not move on until the listed checks pass. If you cannot make a check pass after 3 honest attempts, log the obstacle to `docs/BLOCKERS.md` (create if missing) and continue with the next task in the same phase.
3. **`USER ACTION` blocks are off-limits.** Items labelled `USER ACTION` require human work (training compute, video shoot, signing certs). Stub them with TODOs and keep moving.
4. **Do not break existing flow.** The op-amp demo (`POST /api/sessions/seed/op-amp`) must continue to return a working diagnosis at every checkpoint.
5. **Commit early, often.** After every subsection's acceptance passes, run:
   ```bash
   git add -A && git commit -m "circuitsage: <phase>.<section> <short summary>"
   ```
   If the repo is not a git repo, run `git init && git add -A && git commit -m "circuitsage: baseline"` first.
6. **Verify with the project's own tests.** Run `npm run test:backend` after every backend change. Add new tests where this doc tells you to.
7. **No silent fallbacks.** If Gemma is missing, surface it via `gemma_status` in API responses and a banner in the UI. Do not pretend the deterministic fallback is the model output.
8. **Default model tag** for Ollama is `gemma3:4b` until proven otherwise. The literal string `gemma4:latest` does not currently exist as a published Ollama tag and must be removed from every code path. See Phase 0 Task 0.1 for the verification procedure.
9. **Coding style (per repo conventions):** small files (200–400 lines, hard cap 800), functions ≤ 50 lines, max 4 levels of nesting, organize by feature/domain, no `console.log` / `print` debugging in committed code, no hardcoded secrets, validate inputs at API boundaries.
10. **Anti-pattern alert.** This repo's biggest existing problem is *deterministic theater*: `_fallback_diagnosis()` in `backend/app/services/agent_orchestrator.py` already encodes the correct op-amp answer. Any new circuit must NOT receive a hand-coded answer. The fault catalog (Phase 1) replaces the canned answer with a generic reasoner.

---

## 1. Mission, scope, success criteria

### 1.1 Pitch (do not deviate)

> **Stack traces for circuits.** CircuitSage is an offline-first Gemma-4-powered lab partner that follows electronics students from simulation to oscilloscope. It runs as a classroom microserver — no internet required — and gives every student a patient debugging mentor when the bench is silent.

### 1.2 Tracks

- **Primary:** Future of Education.
- **Secondary:** Digital Equity & Inclusivity (offline microserver framing).
- **Tertiary:** Safety & Trust (low-voltage-only refusal policy, evidence-first reasoning).
- **Stretch prize:** Unsloth Prize ($10K) for best Gemma fine-tune.

### 1.3 Success criteria (must all be true on submission day)

A. The op-amp demo runs end-to-end without internet on a fresh machine after `make install && make demo`.
B. At least **5 distinct circuit topologies** are supported with non-canned diagnosis: inverting op-amp, non-inverting op-amp, RC low-pass filter, voltage divider under load, common-emitter BJT amplifier. (Stretch: full-wave rectifier, Arduino blink with miswired LED.)
C. A **multimodal flow** in the main pipeline: a phone-uploaded breadboard photo or oscilloscope screenshot influences the diagnosis (not just companion mode).
D. A **fine-tuned Gemma LoRA adapter** trained with Unsloth on a circuit-faults dataset is loaded into Ollama and used by default. The adapter name appears in `gemma_status`.
E. An **on-device inference path** is demonstrable: either (a) the iOS app runs Gemma 3n via Cactus or MediaPipe LLM Inference, or (b) a parallel Android prototype runs Gemma 3n via MediaPipe LLM Inference.
F. **Voice in/out** on the iOS bench app: speak a question, hear the answer.
G. **Conversational memory:** chat replies use prior measurements and prior agent turns within a session.
H. The product demo video (≤3 min) shows: (1) a simulation, (2) a real bench failure, (3) CircuitSage diagnosing on-device with no internet, (4) the student fixing the circuit, (5) a generated lab report.
I. The Kaggle writeup is ≤1500 words, names the tracks, names the on-device path, and names the LoRA dataset and Unsloth recipe.
J. CI passes (`npm run test:backend` + frontend type-check).
K. README has correct setup commands that work on a fresh clone.
L. No code path silently masks a failure as a fake answer.

### 1.4 Non-goals (do not build these)

- A general-purpose chatbot.
- An LTspice automation framework (we parse only).
- Real OCR of arbitrary scope screens (we do schematic/measurement vision via Gemma vision, with deterministic fallback messaging).
- High-voltage / mains debugging (refused by safety policy).
- Cloud SaaS deployment.

---

## 2. Competition snapshot (read once, internalize)

- **Judging weights:** Impact & Vision, Technical Execution, Communication. Approximately equal. Judges punish ambiguous user targeting and reward "one user, one workflow" focus.
- **Required deliverables:** public repo, working demo, technical writeup ≤1500 words, ≤3 min video, cover image.
- **Closest precedent:** Gemma 3n Impact Challenge winners. The single server-side winner was **LENTERA** (offline classroom microserver with Ollama). Mirror its framing.
- **Tier-1 differentiators that won 3n:** on-device inference, fine-tuning (LoRA via Unsloth or MLX), multimodal (vision + voice), specific user targeting, real device demos with target community.
- **Unsloth Prize:** $10K for the best Gemma fine-tune. CircuitSage's circuit-fault dataset is a credible niche.
- **Default Ollama model:** `gemma3:4b` for now; switch to the published Gemma 4 tag if and when it lands during the run. Do **not** invent tags.

---

## 3. Current state audit

### 3.1 What works
- FastAPI backend with sessions, artifacts, measurements, diagnoses, messages, reports.
- One hero scenario (op-amp inverting) with sample data.
- Deterministic tools: `parse_netlist`, `analyze_waveform_csv`, `compare_expected_vs_observed`, `safety_check`, `retrieve_lab_manual`, `generate_report`.
- React/Vite PWA with Studio, Bench, Companion routes.
- Electron desktop companion with screen capture and global hotkey.
- Expo iOS bench companion with camera/library upload.
- Backend tests for tools and the companion endpoint.

### 3.2 What is broken or shallow

Each item is a real bug. Codex must fix all of them in Phase 0 unless explicitly deferred.

- **B1.** `OLLAMA_MODEL` defaults to `gemma4:latest` (`backend/app/config.py:16`), which is not a real published Ollama tag.
- **B2.** `OllamaClient.chat` uses a 12-second httpx timeout (`backend/app/services/ollama_client.py:22`), too short for vision and CPU-only inference.
- **B3.** `_fallback_diagnosis` in `backend/app/services/agent_orchestrator.py:57` hardcodes the op-amp answer. Any other circuit gets the same canned reasoning — *deterministic theater*.
- **B4.** `retrieve_lab_manual` is keyword grep with hand-boosted terms (`backend/app/tools/rag.py:17`), not retrieval.
- **B5.** `chat` endpoint discards conversation history; it re-runs `diagnose_session` from scratch every turn (`backend/app/main.py:520`).
- **B6.** Root `package.json` overrides `react-native: 0.83.6` and `apps/desktop` declares `electron: ^41.5.0`. Neither version exists; iOS and desktop apps may not install on a fresh machine.
- **B7.** `parse_netlist` only parses resistors. Capacitors, inductors, voltage sources, BJTs, diodes are skipped. Op-amp recognition is hardcoded to ref names `Rin`/`Rf`.
- **B8.** Single-file frontend (`frontend/src/main.tsx`, ~650 lines) violates project size guideline (target 200-400 lines, max 800). Hard to demo polish.
- **B9.** Companion vision call uses `format=json` with images (`backend/app/main.py:278`). Some Ollama vision builds reject this combination; needs retry without `format=json` and a deterministic JSON-extract path.
- **B10.** Companion mode is the most novel surface but requires the user to share their screen with the browser; demo-fragile.
- **B11.** No real conversational memory; `messages` table is written but never read.
- **B12.** Safety regex would match "230v" inside any URL or test data → false positive. Needs word-boundary tightening already present, but the wider list lacks current-context fields and there is no explicit allowlist for educational discussion.
- **B13.** `expected_waveform.csv` (only 10 lines visible) does not actually contain a full sine wave; quick demos may misread `vout_peak`.
- **B14.** `frontend/src/main.tsx` polls `/api/sessions/{id}` every 3.5 s indefinitely → no WebSocket; bandwidth is fine locally but hides any backend error from the user.
- **B15.** `AGENT_HANDOFF.md` references files like `docker-compose.yml` and `pyproject.toml` that do not exist; cleanup needed for handoff fidelity.
- **B16.** No Makefile / install script. `README.md` setup is multi-step. Judges may bounce.

### 3.3 What is missing for a winning submission

- Multi-circuit support and a **fault catalog** that drives generic reasoning.
- Real **vector RAG** over an electronics textbook + datasheet corpus.
- **Multimodal in the main flow** (not just companion): photo of breadboard or scope screen feeds into diagnosis.
- **Unsloth LoRA fine-tune** on a circuit fault dataset.
- **On-device inference** path (iOS via Cactus or a separate Android MediaPipe demo).
- **Voice in/out** on iOS.
- **Iterative agentic loop** with native Gemma function calling (multi-step tool use, not single-shot).
- **Conversational memory.**
- **Production polish**: signed APK / TestFlight build, hosted demo URL, proper README, Makefile, real demo video.

---

## 4. Target architecture (what we are building)

```
                   ┌────────────────────┐
                   │  iOS Bench App     │ camera + voice + on-device Gemma 3n (Cactus)
                   └─────────┬──────────┘
                             │ HTTPS (LAN) / on-device
                   ┌─────────▼──────────┐
                   │  Web Studio (PWA)  │ session, artifacts, diagnosis, report
                   └─────────┬──────────┘
                             │
                   ┌─────────▼──────────┐
                   │  Desktop Companion │ Electron screen-watch (optional surface)
                   └─────────┬──────────┘
                             │
                   ┌─────────▼──────────┐
                   │  FastAPI backend   │
                   │                    │
                   │  Agentic loop:     │
                   │  - Safety         ─┐
                   │  - Topology detect ├── tool calls (Gemma 4 fn-calling)
                   │  - Netlist parse   │
                   │  - Wave analysis   │
                   │  - Vision (vis)    │
                   │  - Vector RAG      │
                   │  - Compare         │
                   │  - Hypothesis pick │
                   │  - Report          │
                   └─────────┬──────────┘
                             │ HTTP
                   ┌─────────▼──────────┐
                   │  Ollama (Gemma 4)  │ + LoRA adapter (`circuitsage-lora`)
                   └────────────────────┘

  Knowledge base: backend/app/knowledge/{textbook/, datasheets/, faults/}
  Embeddings:     SQLite + sqlite-vss OR Chroma
  Storage:        SQLite (existing) + vector store
```

Hosted on a single laptop or microserver. iOS connects over LAN. No internet required.

---

## 5. Build plan

Each phase has a budget and a clear definition of done. Stay within the budget; if you blow through, mark the leftover tasks `[deferred]` and proceed.

### Phase 0 — Critical hygiene (budget: 6–10 hours)

**Goal:** the existing demo stops lying. Wrong tags, broken deps, theater fallbacks, and judge-facing rough edges are gone.

#### Task 0.1 — Fix the model tag and verify Ollama

**Files:**
- modify `backend/app/config.py`
- modify `README.md`
- modify `backend/app/services/ollama_client.py`
- create `scripts/check_ollama.sh`

**Spec:**
- Default `Settings.ollama_model` to `gemma3:4b`.
- Allow override via `OLLAMA_MODEL` env var (already present; just change the default).
- Add `Settings.ollama_vision_model` with default `gemma3:4b` — the same model handles vision in current Gemma releases. Still allow override via `OLLAMA_VISION_MODEL`.
- In `OllamaClient.health()`, additionally hit `/api/show?name=<model>` and report `loaded: true|false`. If the model is not present, the `/api/health/model` endpoint returns the missing tag and a hint to run `ollama pull <tag>`.
- Add `scripts/check_ollama.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  base="${OLLAMA_BASE_URL:-http://localhost:11434}"
  model="${OLLAMA_MODEL:-gemma3:4b}"
  echo "Ollama base: $base"
  echo "Model: $model"
  curl -sf "$base/api/tags" >/dev/null || { echo "Ollama not reachable"; exit 1; }
  curl -sf "$base/api/show" -d "{\"name\":\"$model\"}" >/dev/null || {
    echo "Model $model not loaded. Run: ollama pull $model"; exit 1;
  }
  echo "Ollama OK"
  ```
  `chmod +x` it.
- Update `README.md` Ollama section to point at `gemma3:4b` and include `bash scripts/check_ollama.sh`.

**Acceptance:**
- `bash scripts/check_ollama.sh` exits 0 if `ollama serve` is running with `gemma3:4b`.
- `curl localhost:8000/api/health/model` returns `{"available": true, "model": "gemma3:4b", "loaded": true, "models": [...]}` when Ollama is up.
- `grep -r "gemma4:latest" .` returns nothing in tracked files.

#### Task 0.2 — Raise timeouts and add retry

**Files:**
- modify `backend/app/services/ollama_client.py`

**Spec:**
- Bump default `httpx.AsyncClient(timeout=12.0)` to a tuple of `(connect=5, read=120, write=30, pool=5)` for `chat`. Keep `health()` at 3 s.
- Add a single retry on `httpx.ReadTimeout` and `httpx.RemoteProtocolError`. Total maximum retries = 1; do not retry on HTTP 4xx.
- If `format_json=True` and the model rejects (HTTP 400 or 500 with body containing `format`), retry once **without** `format=json` and run `parse_json_response` over the raw output.
- Expose `OllamaClient.chat` returning `dict {"content": str, "raw_status": int, "fallback": bool}` instead of bare `str`. Update all callers (`backend/app/services/agent_orchestrator.py`, `backend/app/main.py:companion_analyze`). Tests must still pass.

**Acceptance:**
- `pytest backend/tests` passes.
- New test `backend/tests/test_ollama_client.py` mocks httpx and asserts: timeout retry, format-json retry without `format`, success path, 4xx no-retry.

#### Task 0.3 — Kill the canned-answer theater

**Files:**
- modify `backend/app/services/agent_orchestrator.py`
- create `backend/app/services/fault_catalog.py`

**Spec:**
- Remove the op-amp-specific block in `_fallback_diagnosis` (lines ~99–110 with the `2.8 V` + `4.7 V peak` magic).
- Replace with a topology-aware reasoner that consults `fault_catalog` (Phase 1 builds the actual catalog; for Phase 0, ship the scaffolding with op-amp populated).
- The new fallback path:
  1. Determine `topology` from `parse_netlist(...)` or `session.experiment_type`.
  2. Look up `fault_catalog.candidates(topology, comparison)`. Returns `list[Fault]`.
  3. Pick the highest-confidence candidate. If none match, return a generic `"Need more evidence"` shape with a real `next_measurement` produced by the catalog's measurement planner.
  4. Never produce a `"resolved"` status from the fallback — only from the LLM path. The fallback's strongest output is `"diagnosing"` with `confidence: medium_high`.
- `fault_catalog.py` schema (Phase 0 minimum):
  ```python
  from dataclasses import dataclass

  @dataclass
  class Fault:
      id: str
      name: str
      why: str
      base_confidence: float
      requires_measurements: list[str]
      verification_test: str

  CATALOG: dict[str, list[Fault]] = {
      "op_amp_inverting": [
          Fault(
              id="floating_noninv_input",
              name="Floating non-inverting input",
              why=(
                  "An inverting op-amp needs the non-inverting input tied to circuit "
                  "ground. A floating reference can drag the output to a rail."
              ),
              base_confidence=0.78,
              requires_measurements=["non_inverting_input_voltage"],
              verification_test="Tie V+ to ground with a wire and re-measure Vout.",
          ),
          Fault(
              id="missing_feedback",
              name="Open or wrong feedback path",
              why="Without negative feedback, the op-amp goes open-loop and saturates.",
              base_confidence=0.55,
              requires_measurements=["resistance_rf"],
              verification_test="Power off, ohm-meter Rf between Vout and inverting node.",
          ),
          Fault(
              id="rail_imbalance",
              name="Power rail or ground problem",
              why="A missing or unequal rail can clamp the output.",
              base_confidence=0.35,
              requires_measurements=["v_supply_pos", "v_supply_neg", "v_ground"],
              verification_test="Measure both rails to circuit ground.",
          ),
      ],
  }

  def candidates(topology: str, comparison: dict) -> list[Fault]:
      return CATALOG.get(topology, [])

  def planner_next_measurement(topology: str, taken: set[str]) -> dict:
      faults = CATALOG.get(topology, [])
      for fault in faults:
          for need in fault.requires_measurements:
              if need not in taken:
                  return {
                      "label": need,
                      "expected": "topology-dependent",
                      "instruction": f"Measure {need} per the verification test for '{fault.name}'.",
                  }
      return {
          "label": "general_inspection",
          "expected": "documented bench observation",
          "instruction": "Inspect supply rails, ground reference, and feedback continuity.",
      }
  ```
- The orchestrator imports from `fault_catalog`. The op-amp-specific knowledge that used to live in `_fallback_diagnosis` now lives in `CATALOG["op_amp_inverting"]`.

**Acceptance:**
- `pytest backend/tests/test_tools.py` still passes.
- New test `backend/tests/test_fault_catalog.py`:
  - asserts `candidates("op_amp_inverting", ...)` returns 3 entries with the expected ids.
  - asserts `candidates("unknown_topology", ...)` returns `[]`.
  - asserts `planner_next_measurement("op_amp_inverting", set())["label"] == "non_inverting_input_voltage"`.
- `curl -X POST localhost:8000/api/sessions/seed/op-amp` still returns a coherent diagnosis whose `likely_faults[0].fault` is "Floating non-inverting input" (label can change; the *id* must match).
- A new test `test_orchestrator_unknown_topology.py` creates a session whose experiment_type is `"unknown"` and verifies the diagnosis returns `"Need more evidence"` style output, NOT the op-amp magic strings.

#### Task 0.4 — Fix broken dependency overrides

**Files:**
- modify root `package.json`
- modify `apps/desktop/package.json`
- modify `apps/ios/package.json` (verify and adjust if pinned to non-existent version)

**Spec:**
- Drop `react-native: 0.83.6` from root `overrides`. Pin to a real published version. The current production line at the time of writing is **0.76.x**; use `0.76.5`. If the iOS app bundles successfully with a different version, document it in `apps/ios/package.json` and adjust.
- In `apps/desktop/package.json`, replace `electron: ^41.5.0` with the latest stable Electron at install time (verify with `npm view electron version`); if uncertain, pin to **`^33.0.0`**.
- Run `npm install` from root and from `apps/desktop`. Resolve any peer-dep complaints by lifting versions, not by adding `--legacy-peer-deps` flags.
- Run `npm --prefix apps/desktop run check` and ensure it passes.
- Run `npm --prefix frontend run build` and ensure it produces a clean `dist/`.

**Acceptance:**
- `npm install` at root completes without `ERESOLVE` errors.
- `npm --prefix apps/desktop run check` exits 0.
- `npm --prefix frontend run build` exits 0.
- `npm --prefix apps/ios install` (or `npx expo install --check`) reports OK or a small list of fixable advisories.

#### Task 0.5 — Truthful UI banners and `gemma_status`

**Files:**
- modify `frontend/src/main.tsx` (or new module per Phase 5 split)
- modify `backend/app/main.py` (`/api/health/model` already added in 0.1)

**Spec:**
- Studio page polls `/api/health/model` every 10 s. If the response is not available or the model is not loaded, render a small amber banner: `"Gemma not loaded — running in deterministic mode. Run: ollama pull gemma3:4b"`.
- Diagnosis card displays `gemma_status` chip: green for `ollama_gemma`, amber for `deterministic_fallback`, red for `blocked_by_safety`.
- No silent reskinning of fallback as "AI answer".

**Acceptance:**
- With Ollama down, the Studio shows the amber banner and the diagnosis card chip says `deterministic_fallback`.
- With Ollama up and `gemma3:4b` loaded, the banner is hidden and the chip says `ollama_gemma`.

#### Task 0.6 — Makefile and one-shot install

**Files:**
- create `Makefile`
- create `scripts/install.sh`
- modify `README.md`

**Spec:**
- `Makefile` targets:
  ```
  make install          # bootstraps backend venv + npm installs + pulls model
  make demo             # backend up, frontend up, opens browser to op-amp seed
  make test             # backend + frontend tests
  make lint             # ruff + tsc -b --noEmit
  make clean            # nukes venv, node_modules, dist
  ```
- `scripts/install.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  python3.12 -m venv backend/.venv
  source backend/.venv/bin/activate
  pip install -U pip
  pip install -r backend/requirements.txt
  npm install
  npm --prefix frontend install
  npm --prefix apps/desktop install
  npm --prefix apps/ios install || true
  if command -v ollama >/dev/null 2>&1; then
    ollama pull "${OLLAMA_MODEL:-gemma3:4b}"
  else
    echo "Ollama not installed. See https://ollama.com/download"
  fi
  echo "Install complete. Run: make demo"
  ```
- `make demo` brings backend up in the background, frontend dev server in foreground, and `open http://localhost:5173`.

**Acceptance:**
- On a fresh clone, `make install && make demo` reaches a working Studio in under 5 minutes (assuming model already cached).
- `make test` exits 0.

#### Task 0.7 — README rewrite

**Files:**
- modify `README.md`

**Spec:**
- Top of README: tagline, one-paragraph pitch, screenshot/gif of the demo.
- "Quickstart": `make install && make demo`.
- "Tracks" section listing Future of Education + Digital Equity + Safety.
- "On-device path" note pointing at the iOS build (Phase 4).
- "Fine-tune" note pointing at `train/README.md` (Phase 3).
- Drop references to non-existent files (`docker-compose.yml`, `pyproject.toml`) unless those files are added later.

**Acceptance:**
- README opens with the tagline, has a working Quickstart, and links to all build phases. No dead links.

---

### Phase 1 — Generalize beyond the op-amp (budget: 1.5–2 days)

**Goal:** five working circuit topologies, real generic diagnosis, a fault catalog used by both the deterministic and LLM paths.

#### Task 1.1 — Expand `parse_netlist` to all SPICE basics

**Files:**
- modify `backend/app/tools/parse_netlist.py`
- create `backend/tests/test_parse_netlist.py` (or extend existing)

**Spec:**
- Parse: R, C, L, V, I, D, Q (BJT), M (MOSFET), X (subcircuit) with reference designators.
- Support SPICE suffixes: `f, p, n, u, m, k, meg, g, t` and bare numerics. Reject ambiguous strings.
- Return:
  ```python
  {
    "components": [...],
    "nodes": [...],          # unique node names
    "sources": [...],        # voltage/current sources with shape "DC 12" or "SIN(0 1 1k)"
    "directives": [...],     # .tran, .ac, .op
    "detected_topology": "op_amp_inverting | op_amp_noninverting | rc_lowpass | "
                         "voltage_divider | bjt_common_emitter | full_wave_rectifier | "
                         "arduino_blink | unknown",
    "computed": {...},       # expected gain, cutoff, etc.
  }
  ```
- **Topology detection** is rule-based:
  - `op_amp_inverting`: presence of an op-amp subcircuit / `Eop`-style controlled source with one resistor between input and inverting node and one resistor between output and inverting node, non-inverting node tied to ground.
  - `op_amp_noninverting`: as above but input drives non-inverting node.
  - `rc_lowpass`: one R in series, one C to ground; compute `f_c = 1/(2 pi R C)`.
  - `voltage_divider`: two R in series across V source, output at the tap; compute `Vout = Vin * R2/(R1+R2)`.
  - `bjt_common_emitter`: a Q with collector resistor, emitter resistor, base bias network.
  - `full_wave_rectifier`: ≥4 D arranged in bridge; compute `Vout_peak ≈ V_in_peak − 2*Vd`.
  - `arduino_blink`: heuristic detector if the artifact is `.ino` (handled in Task 1.5).

**Acceptance:**
- New tests for each topology with a sample netlist in `sample_data/<topology>/`. Each test asserts `detected_topology` and at least one `computed` value.
- Backward compatibility: existing op-amp test still passes.

#### Task 1.2 — Build the full fault catalog

**Files:**
- expand `backend/app/services/fault_catalog.py`
- create `backend/app/services/fault_data/<topology>.json` for each topology

**Spec:**
- Move catalog data out of Python and into JSON files (one per topology), loaded at import time.
- For each topology, encode 3–6 faults with: `id, name, why, base_confidence, requires_measurements, verification_test, fix_recipe`.
- Confidence is dynamically scaled by the orchestrator using available measurements: when a fault's required measurement is satisfied and consistent with the fault's signature, scale confidence up to a cap of 0.92; if the measurement contradicts, scale to ≤ 0.15.
- Add `fault_catalog.score(topology, comparison, measurements) -> list[ScoredFault]` returning sorted candidates.

**Acceptance:**
- Each topology returns ≥3 distinct fault candidates from `score(...)`.
- For op-amp inverting: when `V_noninv = 2.8 V` is in the measurements, `floating_noninv_input` scores ≥ 0.85; when `V_noninv = 0.0 V`, it scores ≤ 0.15.
- Test file `backend/tests/test_fault_catalog_scoring.py` covers all 5 topologies with seeded measurements.

#### Task 1.3 — Generic agentic diagnosis loop

**Files:**
- modify `backend/app/services/agent_orchestrator.py`
- modify `backend/app/services/prompt_templates.py`

**Spec:**
- Replace the single-shot Gemma call with a small loop:
  1. **Step 1 — Topology grounding.** Construct a system prompt that includes the detected topology, expected behavior, and the fault catalog for that topology (top 5 only).
  2. **Step 2 — Tool calls.** Pass tool schemas via Gemma's function-calling format (Ollama's chat API supports `tools` parameter for compatible models). Tools exposed: `compute_expected_value`, `request_measurement`, `request_image`, `cite_textbook`, `verify_with_simulation`. Stub bodies are fine for Phase 1; real implementations land in Phase 2.
  3. **Step 3 — Final structured diagnosis.** Same JSON schema as today. The LLM merges its reasoning with the deterministic candidates.
- Loop limit: maximum 4 iterations to bound latency.
- If Ollama returns garbage at any step, fall back to the deterministic catalog top pick. Tag `gemma_status` accordingly: `ollama_gemma`, `ollama_partial`, `deterministic_fallback`.
- Persist intermediate `tool_calls` as a list (already partially done).

**Acceptance:**
- `pytest backend/tests` passes.
- Manual test with Ollama up: `POST /api/sessions/seed/op-amp` returns `gemma_status: ollama_gemma` and `tool_calls` includes at least one `request_measurement` event.
- With Ollama down, returns `gemma_status: deterministic_fallback` and the diagnosis matches the catalog's top fault.

#### Task 1.4 — Sample data for new topologies

**Files:**
- create `sample_data/rc_lowpass/{netlist.net, expected_waveform.csv, observed_attenuated.csv, lab_manual_excerpt.md, student_question.txt}`
- create `sample_data/voltage_divider/{...}`
- create `sample_data/bjt_common_emitter/{...}`
- create `sample_data/op_amp_noninverting/{...}`
- modify `backend/app/main.py` (add seed endpoints)

**Spec:**
- Each topology gets a seed endpoint, `POST /api/sessions/seed/<topology>`, mirroring the op-amp endpoint.
- Each scenario has at least one canonical fault designed in. Examples:
  - `rc_lowpass`: cutoff calculated for R=10k, C=100nF (159 Hz). Observed waveform shows attenuation at 100 Hz (impossible if ideal) → fault: "wrong capacitor value".
  - `voltage_divider`: R1=10k, R2=10k, no load expected 6 V; observed under load shows 1.8 V → fault: "load resistance comparable to R2".
  - `bjt_common_emitter`: base bias resistors set to drive saturation by mistake; observed Vc ≈ 0.2 V → fault: "incorrect base bias".
  - `op_amp_noninverting`: gain expected (1+Rf/Rg)=11; observed 1 → fault: "Rg open / not connected".
- Each scenario gets a small landing tile on the Studio home page.

**Acceptance:**
- All 4 new seed endpoints return a session with non-canned diagnosis; `gemma_status` is `ollama_gemma` or `deterministic_fallback`, never the op-amp string template.
- Frontend home shows 5 demo tiles.

#### Task 1.5 — Arduino `.ino` and MATLAB `.m` parsing

**Files:**
- create `backend/app/tools/parse_arduino.py`
- create `backend/app/tools/parse_matlab.py`
- extend `backend/app/main.py:_artifact_kind`

**Spec:**
- `parse_arduino.py`: extract pin assignments (`pinMode(13, OUTPUT)`), `digitalWrite`/`digitalRead` calls, `delay(...)`, and `Serial.println` patterns. Detect a "blink" pattern (alternating `HIGH/LOW` writes with `delay`).
- `parse_matlab.py`: extract variable assignments, plot calls, sampling-rate hints (`fs = ...`). For `.m` files, treat the first 50 non-comment lines as the analysis context.
- These are deliberately small, deterministic parsers; they exist to ground the LLM call, not to fully understand the language.

**Acceptance:**
- New tests parse a sample blink sketch and a sample plot script and produce non-empty structured output.
- `_artifact_kind` correctly labels `.ino` and `.m` files.

#### Task 1.6 — Conversational chat memory

**Files:**
- modify `backend/app/main.py:chat`
- modify `backend/app/services/agent_orchestrator.py`

**Spec:**
- Read the last 8 messages from `messages` table for the session.
- Pass them as a `messages` array to Ollama with proper `role: user|assistant` shape, *before* the structured diagnosis prompt.
- The structured diagnosis schema stays unchanged; the LLM gets context but still emits structured JSON.
- Persist the assistant's natural-language reply (already partially done) and also persist a stripped version of `tool_calls` for traceability.

**Acceptance:**
- A two-turn conversation in the Studio chat panel demonstrably uses turn-1 information in turn-2 output (e.g., user says "I already measured V_noninv at 2.8 V" in turn 1, then asks "what next" in turn 2 — the assistant references the prior measurement).

---

### Phase 2 — Real RAG and multimodal in the main flow (budget: 1.5–2 days)

**Goal:** retrieval is real, schematic / scope photos influence the main diagnosis, not just the companion mode.

#### Task 2.1 — Vector store and corpus ingest

**Files:**
- create `backend/app/services/vectorstore.py`
- create `backend/app/services/embedder.py`
- create `backend/app/knowledge/{textbook/, datasheets/, faults/}` (directory; populate via `scripts/ingest_corpus.py`)
- create `scripts/ingest_corpus.py`
- modify `backend/requirements.txt`

**Spec:**
- Add deps: `chromadb==0.5.20` (or `sqlite-vss` if Chroma's wheel is heavy). Default to **Chroma in DuckDB+Parquet mode**, persistent at `backend/app/data/chroma/`.
- `embedder.py`: prefer Ollama's embedding endpoint (`/api/embeddings` with `nomic-embed-text` or `mxbai-embed-large`). Fallback to `sentence-transformers` `all-MiniLM-L6-v2` if Ollama embeddings are unavailable.
- `vectorstore.py`: `ingest(doc_id, text, metadata)`, `query(text, k=5, filter=None) -> list[Hit]`.
- `scripts/ingest_corpus.py`: walks `backend/app/knowledge/` and ingests every `.md`, `.txt`, `.pdf` (use `pypdf`). Records: source filename, paragraph index, text, embedding.
- Seed corpus content:
  - `knowledge/textbook/op_amp.md`, `rc_filters.md`, `bjt_basics.md`, `voltage_divider.md`, `safety.md`. Pull from public-domain or CC-licensed sources only; note license in `knowledge/SOURCES.md`. **USER ACTION** if licensing is uncertain — ship our own concise notes written by Codex (≤500 lines per topic), under our own license.
  - `knowledge/datasheets/`: short curated extracts (pin maps, abs max ratings) for: TL081, LM741, 2N3904, 1N4148, NE555. Same licensing rule.
  - `knowledge/faults/`: long-form fault explanations matching `fault_catalog` ids. The catalog references these by id.

**Acceptance:**
- `python scripts/ingest_corpus.py` populates the vector store and prints a per-source row count.
- `python -c "from backend.app.services.vectorstore import query; print(query('non-inverting input floating', k=3))"` returns 3 hits with the expected fault doc near the top.

#### Task 2.2 — Replace `retrieve_lab_manual` with the real retriever

**Files:**
- modify `backend/app/tools/rag.py`
- modify `backend/app/services/agent_orchestrator.py`

**Spec:**
- New `rag.retrieve(query: str, *, topology: str | None = None, k: int = 4) -> dict`:
  - Run a vector search.
  - Optionally filter by `metadata.topology == topology` if provided.
  - Always include the session's uploaded manual artifacts as additional sources, weighted higher than corpus matches.
  - Return:
    ```python
    {
      "snippets": [{"source": str, "text": str, "score": float}, ...],
      "from_corpus": int,
      "from_session": int,
    }
    ```
- Orchestrator uses `topology` from netlist parsing as the filter.

**Acceptance:**
- `pytest backend/tests/test_rag.py` covers: query returns the right doc; filter by topology narrows results; session artifacts appear at top when provided.
- Op-amp seed run includes a `retrieve` tool call whose top hit is from `knowledge/faults/floating_noninv_input.md`.

#### Task 2.3 — Vision in the main pipeline

**Files:**
- modify `backend/app/services/agent_orchestrator.py`
- create `backend/app/tools/vision.py`
- modify `backend/app/schemas.py`

**Spec:**
- New tool `vision.describe_artifact(artifact_id) -> dict`. Loads the image, base64-encodes it, calls Ollama with a tightly scoped prompt: identify components, count terminals, read any visible numeric labels, identify the circuit topology if visible.
- `diagnose_session(...)`:
  - If the session has at least one `image` artifact tagged as `breadboard` or `oscilloscope`, run `vision.describe_artifact` for each (cap to 2 images per diagnosis, most recent first) and add the structured output to the LLM context.
  - In the deterministic fallback path, vision results are used to bias `fault_catalog.score` (e.g., a visible disconnected wire to the non-inverting input bumps `floating_noninv_input` confidence).
- Add an artifact `kind` of `oscilloscope` and `breadboard` to the literal type and frontend dropdown so users can label uploads precisely.

**Acceptance:**
- New test `backend/tests/test_vision_tool.py` mocks Ollama and asserts the prompt and output handling.
- A new sample image (`sample_data/op_amp_lab/breadboard_disconnected.png` — copy of the existing breadboard placeholder for now; **USER ACTION** to replace with real photo) labelled `breadboard` is part of the seed; running diagnosis produces a `tool_calls` entry of type `describe_artifact`.

#### Task 2.4 — Fix the companion endpoint's vision-with-JSON bug

**Files:**
- modify `backend/app/main.py:companion_analyze`

**Spec:**
- Stop sending `format=json` together with `images=[...]` in a single call. Separate flow:
  1. Call vision **without** `format=json` and ask for "describe what you see, then propose next actions".
  2. Pass the vision text into a second non-vision call with `format=json` to coerce the structure.
- Bound total time to `vision_timeout + structuring_timeout`. If either step fails, fall back to the deterministic-per-workspace path.

**Acceptance:**
- Companion analysis returns coherent JSON with `mode: ollama_gemma_vision` when both calls succeed.
- A unit test mocks both calls and asserts the two-step flow.

---

### Phase 3 — Unsloth LoRA fine-tune (budget: 2–4 days incl. USER compute)

**Goal:** ship a working LoRA adapter trained on a circuit-fault Q&A dataset, served via Ollama, used by default. Eligible for the Unsloth Prize.

#### Task 3.1 — Build the dataset

**Files:**
- create `train/dataset/build.py`
- create `train/dataset/raw/` (curated source texts)
- create `train/dataset/circuitsage_qa.jsonl` (output)

**Spec:**
- Generate a JSONL with 5–10k examples of circuit-fault Q&A in the format Unsloth expects for chat fine-tuning:
  ```json
  {"messages": [
    {"role": "system", "content": "You are CircuitSage, an electronics lab partner."},
    {"role": "user", "content": "I built an inverting op-amp ... output stuck at +12 V ..."},
    {"role": "assistant", "content": "{\"experiment_type\": \"op_amp_inverting\", ...}"}
  ]}
  ```
- Sources for `train/dataset/raw/`:
  - The 5 topology lab manuals from `knowledge/textbook/` (Phase 2).
  - The fault catalog (`fault_data/*.json`).
  - 200–500 hand-written Q&A seeds (Codex generates these from the fault catalog using a templated procedure; document the procedure in `train/dataset/README.md`).
  - Augmentations: paraphrase each seed into 5 variants using a small local LLM (Gemma 3:4b via Ollama). Build the augmenter as a script: `python train/dataset/augment.py --in seeds.jsonl --out augmented.jsonl --variants 5`.
- Each example must include:
  - The same structured-JSON output schema we use at runtime.
  - A safety branch sample: 5% of examples ask about mains/HV and the assistant returns the safety-refusal JSON shape.

**Acceptance:**
- `train/dataset/circuitsage_qa.jsonl` exists with at least 5,000 lines.
- A linter `train/dataset/validate.py` verifies every line is valid JSON and matches the schema.

#### Task 3.2 — Unsloth training notebook

**Files:**
- create `train/unsloth_lora.ipynb`
- create `train/README.md`

**Spec:**
- Notebook trains an Unsloth LoRA adapter on top of `unsloth/gemma-3-4b-it` (or whichever Gemma 3 / Gemma 4 is available on Unsloth at run time; check `https://docs.unsloth.ai/get-started/all-our-models` and pin the exact model id in a notebook cell).
- Use 4-bit quantized base model, rank 16 LoRA, alpha 32, target modules `["q_proj","k_proj","v_proj","o_proj"]`, learning rate 2e-4, 3 epochs, max seq length 4096.
- Save adapter to `train/output/circuitsage-lora/` and produce a GGUF merge into `train/output/circuitsage-lora-q4_k_m.gguf` for Ollama compatibility.
- `train/README.md` documents:
  - How to run on Kaggle (free T4) or Colab Pro (A100). **USER ACTION**: training itself runs on a Kaggle/Colab session; Codex cannot train locally on a Mac.
  - How to download the merged GGUF and load it into Ollama via a `Modelfile` (Task 3.3).

**Acceptance:**
- Notebook runs end-to-end on Kaggle's free GPU in ≤90 minutes.
- The notebook saves both the LoRA adapter directory and the GGUF.

#### Task 3.3 — Ollama Modelfile and integration

**Files:**
- create `train/output/circuitsage.Modelfile`
- modify `scripts/install.sh`
- modify `backend/app/config.py`

**Spec:**
- Modelfile:
  ```
  FROM ./circuitsage-lora-q4_k_m.gguf
  TEMPLATE """{{ .System }}
  {{ .Prompt }}"""
  PARAMETER temperature 0.3
  PARAMETER top_p 0.9
  PARAMETER num_ctx 4096
  SYSTEM """You are CircuitSage, an offline electronics lab partner."""
  ```
- `install.sh` adds: `if [ -f train/output/circuitsage-lora-q4_k_m.gguf ]; then ollama create circuitsage:latest -f train/output/circuitsage.Modelfile; fi`.
- `config.py` default updates: if `circuitsage:latest` is loaded in Ollama, prefer it over `gemma3:4b`.

**Acceptance:**
- After running install with a downloaded GGUF, `ollama list` shows `circuitsage:latest`.
- The diagnosis endpoint reports `gemma_status: ollama_gemma` with model name `circuitsage:latest` in metadata.

---

### Phase 4 — On-device inference path (budget: 2–4 days)

**Goal:** demonstrate Gemma running on a phone with no internet. Two acceptable paths, in order of preference. Pick A; fall back to B if blocked.

#### Path A — iOS via Cactus (preferred)

**Files:**
- modify `apps/ios/package.json`
- create `apps/ios/src/cactus/CactusClient.ts`
- modify `apps/ios/App.tsx`
- update `apps/ios/app.json`

**Spec:**
- Add `cactus-react-native` (or current Cactus React Native binding; verify package name at run time).
- Bundle a small Gemma 3n quantized model (.task or .gguf depending on Cactus support) under `apps/ios/assets/models/gemma-3n-2b-q4.<ext>`. **USER ACTION**: download the model from the official Gemma weights distribution, place file, accept license. Cactus loads from `assets`.
- Add a UI toggle: `Local model (offline)` vs `Server (LAN)`.
- When local is selected, the Bench app runs inference fully on-device:
  - Prompt: same structured-diagnosis schema.
  - Input: bench question + last 5 measurements + optional photo (if Cactus build supports vision; otherwise text-only).
- Both paths share `apps/ios/src/types.ts` so the rest of the UI is unchanged.

**Acceptance:**
- Run `npx expo run:ios` on a physical device, toggle local mode, ask a question with airplane mode on, get a structured response.
- A short README at `apps/ios/README.md` documents bundling the model and TestFlight steps.

#### Path B — Android MediaPipe LLM Inference (fallback)

**Files:**
- create `apps/android/` (Android Studio project, Kotlin, Gradle)
- create `apps/android/README.md`

**Spec:**
- Standalone Android Studio project that uses the MediaPipe LLM Inference API to run Gemma 3n.
- Single screen: text question, camera button, response area.
- Mirrors the `/api/companion/analyze` schema, fully on-device.
- Install via `./gradlew installDebug`.

**Acceptance:**
- An installable APK runs offline on an Android device, returns a coherent response.

---

### Phase 5 — Voice + agent loop polish (budget: 1–2 days)

#### Task 5.1 — Voice on iOS

**Files:**
- modify `apps/ios/App.tsx`
- add deps: `expo-av`, `react-native-voice` or `expo-speech-recognition`.

**Spec:**
- Add a microphone button. Hold-to-record, release-to-send. Use system STT for English first.
- Add `expo-speech` for TTS playback of the answer.
- Persist recordings as artifacts when the session is set.

**Acceptance:**
- On a physical iPhone, hold mic, speak a question, see the question text fill in, get an answer back, hear it spoken.

#### Task 5.2 — Iterative agent loop with native function calling

**Files:**
- modify `backend/app/services/agent_orchestrator.py`
- create `backend/app/services/tool_schemas.py`

**Spec:**
- Define tool schemas (JSON Schema) for: `parse_netlist`, `analyze_waveform_csv`, `compare_expected_vs_observed`, `safety_check`, `retrieve_rag`, `describe_image`, `request_measurement`. Pass these in Ollama's `tools` parameter for any model that supports it.
- Loop:
  1. Call model with system prompt + context + tools.
  2. If model returns tool calls, execute them, append outputs, loop.
  3. If no tool calls, parse final structured JSON.
  4. Cap at 6 iterations; bail to deterministic fallback on failure.

**Acceptance:**
- Manual test shows >1 tool call in the trace for a typical diagnosis.
- Existing tests pass.

---

### Phase 6 — Production polish (budget: 1–2 days)

#### Task 6.1 — Frontend split and design polish

**Files:**
- split `frontend/src/main.tsx` into `frontend/src/{App.tsx, routes/{Home,Studio,Bench,Companion}.tsx, components/*, hooks/*, lib/*}`. Each ≤400 lines.
- add `frontend/src/components/{DiagnosisCard, FaultRanking, EvidenceStrip, ToolTimeline, ChatPanel, GemmaStatusBanner}.tsx`.
- add a typed router (e.g. `wouter`).

**Spec:**
- Visually: stick to existing dark theme. Add a left rail with topology icons (op-amp, RC, voltage divider, BJT, Arduino). Bottom-right toast for `gemma_status` changes.
- Accessibility: keyboard nav, focus states, alt text on QR + scope images.

**Acceptance:**
- `npm --prefix frontend run build` exits 0.
- All routes still work; no regressions in the op-amp demo.

#### Task 6.2 — CI

**Files:**
- create `.github/workflows/ci.yml`

**Spec:**
- Jobs: backend pytest, frontend tsc + build, desktop check, ios `expo-doctor` (best-effort).
- Cache pip and npm.

**Acceptance:**
- CI passes on push.

#### Task 6.3 — Hosted demo (optional, **USER ACTION**)

- Deploy backend to Fly.io / Railway with a small CPU-only container that proxies to a remote Ollama or runs `gemma3:4b` if the dyno can hold it.
- Frontend on Vercel.
- Document URLs in README.

---

### Phase 7 — Submission materials (budget: 1 day, mostly **USER ACTION**)

#### Task 7.1 — Demo video script and shotlist

**Files:**
- modify `docs/DEMO_SCRIPT.md`

**Spec:**
- Final 3-min cut: 0:00 hook (silent failure), 0:25 Studio (load demo, show artifacts and tool calls), 1:00 Bench (phone QR + photo), 1:30 on-device offline diagnosis, 2:10 fix and re-test, 2:35 lab report, 2:50 outro.
- **USER ACTION:** record the video. Codex prepares the script, captions, and B-roll list.

#### Task 7.2 — Kaggle writeup

**Files:**
- modify `docs/KAGGLE_WRITEUP_DRAFT.md`

**Spec:**
- Final draft ≤1500 words. Sections: Problem, Solution, Tracks, Architecture, Multimodal, Fine-tune, On-device, Safety, Reproducibility, Future Work.
- Include exact links to: repo, video, gallery, dataset, LoRA adapter.

#### Task 7.3 — Cover image and gallery

**Files:**
- modify `docs/MEDIA_GALLERY.md`

**Spec:**
- One 1600×900 cover image. Gallery: Studio screenshot, Bench app screenshot, Companion screenshot, on-device demo, scope before/after, lab report.
- **USER ACTION**: take the screenshots once Phase 6 lands.

---

## 6. File-by-file change reference

The single source of truth for what each phase touches. Codex updates this as it executes.

| Path | Status | Phase | Notes |
|------|--------|-------|-------|
| `backend/app/config.py` | modify | 0.1 | model defaults, vision model |
| `backend/app/services/ollama_client.py` | modify | 0.1, 0.2 | health, retries, format-json fallback |
| `scripts/check_ollama.sh` | create | 0.1 | preflight |
| `backend/app/services/agent_orchestrator.py` | modify | 0.3, 1.3, 2.3, 5.2 | catalog wiring, agent loop |
| `backend/app/services/fault_catalog.py` | create | 0.3, 1.2 | scaffolding then full catalog |
| `backend/app/services/fault_data/*.json` | create | 1.2 | per-topology data |
| `backend/app/tools/parse_netlist.py` | modify | 1.1 | full SPICE basics |
| `backend/app/tools/parse_arduino.py` | create | 1.5 | .ino |
| `backend/app/tools/parse_matlab.py` | create | 1.5 | .m |
| `sample_data/<topology>/*` | create | 1.4 | 4 new scenarios |
| `backend/app/services/vectorstore.py` | create | 2.1 | Chroma wrapper |
| `backend/app/services/embedder.py` | create | 2.1 | Ollama-first, sentence-transformers fallback |
| `backend/app/knowledge/**` | create | 2.1 | corpus seed |
| `scripts/ingest_corpus.py` | create | 2.1 | corpus ingest |
| `backend/app/tools/rag.py` | modify | 2.2 | real retriever |
| `backend/app/tools/vision.py` | create | 2.3 | image → structured |
| `backend/app/main.py` | modify | 0.5, 1.4, 2.3, 2.4 | health, seeds, vision wire-in, companion fix |
| `backend/app/schemas.py` | modify | 1.4, 2.3 | new artifact kinds |
| `backend/tests/**` | create/modify | every phase | one test per behavior |
| `train/dataset/build.py` | create | 3.1 | dataset |
| `train/dataset/circuitsage_qa.jsonl` | create | 3.1 | dataset output |
| `train/unsloth_lora.ipynb` | create | 3.2 | training |
| `train/output/circuitsage.Modelfile` | create | 3.3 | Ollama load |
| `apps/ios/src/cactus/*` | create | 4.A | on-device |
| `apps/android/**` | create | 4.B | fallback on-device |
| `frontend/src/{App,routes,components,hooks,lib}/**` | refactor | 6.1 | split + polish |
| `Makefile`, `scripts/install.sh` | create | 0.6 | bootstrap |
| `README.md` | modify | 0.7 | rewrite |
| `docs/DEMO_SCRIPT.md` | modify | 7.1 | shooting plan |
| `docs/KAGGLE_WRITEUP_DRAFT.md` | modify | 7.2 | final writeup |
| `.github/workflows/ci.yml` | create | 6.2 | CI |
| `docs/BLOCKERS.md` | create | as needed | log obstacles |
| Root `package.json`, `apps/desktop/package.json` | modify | 0.4 | dep pins |

---

## 7. Verification protocol

Run after every phase:

```bash
# Backend
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q

# Frontend
npm --prefix frontend run build

# Desktop
npm --prefix apps/desktop run check

# Demo smoke test (Ollama must be up)
bash scripts/check_ollama.sh
curl -s -X POST localhost:8000/api/sessions/seed/op-amp | jq '.seed_diagnosis | {confidence, gemma_status, top: .likely_faults[0].fault}'
```

Phase-end gates:

- **Phase 0 done:** all tests pass, no `gemma4:latest` references, the op-amp demo reports `gemma_status: ollama_gemma` (or `deterministic_fallback` with the correct catalog top fault if Ollama is intentionally down for the test), broken dep overrides are removed, `make demo` works.
- **Phase 1 done:** five seed endpoints exist, each returns a non-canned diagnosis grounded in the fault catalog, the chat endpoint uses prior turns.
- **Phase 2 done:** vector RAG returns expected hits, vision describes a breadboard photo and biases the catalog scoring, companion endpoint no longer mixes `format=json` with images.
- **Phase 3 done:** `circuitsage:latest` model loads in Ollama, `gemma_status` reports the LoRA model id, dataset linter exits 0.
- **Phase 4 done:** an on-device inference path works in airplane mode on a real device.
- **Phase 5 done:** voice in/out works on iOS; the agent loop produces ≥1 tool call per typical diagnosis.
- **Phase 6 done:** frontend split, CI green.
- **Phase 7 done:** writeup ≤1500 words, video script ready, screenshots captured.

---

## 8. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gemma 4 Ollama tag drifts during the run | medium | medium | Pin `gemma3:4b` until proven; gate model selection behind config and surface in UI. |
| Unsloth LoRA training fails on Kaggle free tier | medium | medium | Provide a fallback Modelfile that uses base `gemma3:4b` so submission still works. Document Colab Pro path. |
| Cactus on iOS unsupported for the chosen Gemma quant | medium | high | Drop to Path B (Android MediaPipe LLM Inference). |
| Vector store deps don't install on mac/arm | low | medium | Chroma supports DuckDB+Parquet; if Chroma's heavy, switch to `sqlite-vss`. |
| Ollama vision rejects multi-call format combos | medium | low | Already handled in 0.2 (format-json retry) and 2.4 (split vision/structuring). |
| Time budget overrun before Phase 4 | medium | high | Phase priority order: 0 > 1 > 2 > 3 > 6.1 (UI polish) > 7 > 4 > 5. If only Phases 0–3 + 6.1 + 7 land, the submission is still credible. Phase 4 is a strong nice-to-have but not required for the General/Impact prizes. |
| LoRA adapter destabilizes the base model on edge questions | medium | medium | Hold out 200 examples for eval; if regression > 10% on safety questions, lower learning rate or epochs. |
| Sample-data licensing | medium | low | All `knowledge/textbook/*.md` written from scratch by Codex, MIT-licensed in `LICENSE`. |
| Demo video shoot delayed | high | high | Codex pre-renders an animated demo (Lottie or SVG-anim) as a fallback B-roll; user records voiceover only. |

---

## 9. Glossary and appendix

### 9.1 Topology cheat sheet (for prompts and sample data)

- **Op-amp inverting:** `Vout = -(Rf/Rin) * Vin`. V+ tied to ground. Common faults: floating V+, open Rf, rail imbalance.
- **Op-amp non-inverting:** `Vout = (1 + Rf/Rg) * Vin`. Common faults: open Rg, no feedback path, common-mode violation.
- **RC low-pass:** `f_c = 1/(2 pi R C)`. Common faults: wrong C value, source impedance loading, broken ground.
- **Voltage divider:** `Vout = Vin * R2 / (R1 + R2)` (unloaded). Common faults: load comparable to R2, source-impedance loading, bad ground.
- **BJT common-emitter:** voltage gain ≈ `-Rc / re'`. Common faults: incorrect base bias (saturation/cutoff), emitter resistor open, missing decoupling.
- **Full-wave rectifier (bridge):** `Vout_peak ≈ Vin_peak − 2*V_d`. Common faults: reversed diode, missing filter cap, load too heavy.
- **Arduino blink with miswired LED:** LED in wrong polarity or no series resistor. Common faults: LED reversed, no current-limit R, GPIO miswired.

### 9.2 Default prompts

System prompt (per Task 1.3):

```
You are CircuitSage, an offline electronics lab partner.
You guide students through circuit debugging using evidence: simulation expectations,
bench measurements, and visible photos. You ask for the next useful measurement
before guessing. You return strict JSON in the requested schema.
You refuse detailed live debugging for mains, high-voltage, SMPS primary,
CRT/flyback, EV battery, microwave, or large capacitor banks.
```

Structured-diagnosis schema (already used; do not change without tests):

```json
{
  "experiment_type": "string",
  "expected_behavior": {"...": "..."},
  "observed_behavior": {"summary": "string", "evidence": ["..."]},
  "likely_faults": [{"fault": "string", "confidence": 0.0, "why": "string"}],
  "next_measurement": {"label": "string", "expected": "string", "instruction": "string"},
  "safety": {"risk_level": "low_voltage_lab|high_voltage_or_mains", "warnings": ["..."]},
  "student_explanation": "string",
  "confidence": "low|medium|medium_high|high",
  "session_status": "diagnosing|resolved"
}
```

### 9.3 Required environment variables

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b              # auto-upgrade to circuitsage:latest if loaded
OLLAMA_VISION_MODEL=gemma3:4b
OLLAMA_EMBED_MODEL=nomic-embed-text
FRONTEND_ORIGIN=http://localhost:5173
CIRCUITSAGE_DEV=1
CIRCUITSAGE_API_URL=http://127.0.0.1:8000   # consumed by desktop and iOS apps
```

### 9.4 Reference URLs (verified at planning time, re-verify if stale)

- Gemma 4 Good Hackathon overview — https://www.kaggle.com/competitions/gemma-4-good-hackathon
- Gemma 3n developer recap — https://blog.google/innovation-and-ai/technology/developers-tools/developers-changing-lives-with-gemma-3n/
- LENTERA writeup (Ollama Prize, our architectural mirror) — search "LENTERA Gemma 3n" for the most recent post.
- Unsloth docs — https://docs.unsloth.ai/
- Ollama Modelfile reference — https://github.com/ollama/ollama/blob/main/docs/modelfile.md
- MediaPipe LLM Inference — https://ai.google.dev/edge/mediapipe/solutions/genai/llm_inference
- Cactus — https://github.com/cactus-compute (verify the React Native binding name and current support matrix at install time)

### 9.5 Cut lines

If running short on time, cut in this order (reverse-priority):

1. Phase 5.1 Voice (iOS).
2. Phase 4 (on-device): keep Path B Android prototype only if Path A fails fast.
3. Phase 6.2 CI (manual verification in PRs).
4. Phase 4 entirely: ship "offline classroom microserver" framing only.
5. Phase 1.5 Arduino/MATLAB parsers.
6. Voltage divider as a topology (keep op-amp inverting + non-inverting + RC + BJT).

Never cut: Phase 0, Phase 1.1–1.4, Phase 2, Phase 3, Phase 6.1 (UI split), Phase 7 (writeup + script).

---

## 10. Sign-off checklist (review before submitting)

- [ ] `make install && make demo` works on a fresh clone.
- [ ] All 5 seed scenarios produce non-canned diagnoses.
- [ ] `gemma_status` truthfully reports source model; LoRA model id appears when loaded.
- [ ] At least one breadboard or scope image affects the diagnosis.
- [ ] Vector RAG returns the expected fault doc near the top for op-amp seed.
- [ ] iOS app runs in airplane mode and returns a coherent answer (Phase 4 Path A or B).
- [ ] Voice in/out works on iOS (Phase 5).
- [ ] CI green on the submission commit.
- [ ] README, writeup, demo script, gallery updated.
- [ ] Tagged release `v1.0.0-submission`.
- [ ] Submitted to Kaggle with public repo URL, video URL, and writeup.

End of plan.
