# CircuitSage — Winning Forward Plan

**Read order:** `WINNING_BUILD_PLAN.md` → `PHASE_3_5_PATCH.md` → **this doc**.
**Audience:** the same Codex agent. This is the long-horizon backlog after Phases 0–3 + 3.5 patch land.
**Today (planning anchor):** 2026-05-05.
**Hard deadline:** 2026-05-18 23:59 UTC. Roughly 13 days; assume 8 working days of focused agent runs.
**Pitch (do not deviate):** *"Stack traces for circuits."* An offline Gemma-4-powered classroom microserver that turns silent bench failures into a step-by-step debugging path.

---

## 0. Competition snapshot (verified 2026-05-05)

Treat this as authoritative; supersedes the original `WINNING_BUILD_PLAN.md` Section 2 where they conflict.

### 0.1 Tracks (five, pick two)
- **Future of Education** — primary.
- **Digital Equity & Inclusivity** — secondary, anchored by offline-first + localization + accessibility.
- **Safety & Trust** — tertiary, anchored by low-voltage-only refusal + uncertainty calibration.
- *(Health & Sciences and Global Resilience are not the focus; do not design for them.)*

### 0.2 Deliverables
- Public repo with reproducible setup.
- Working demo (URL or local instructions).
- Technical writeup (target ≤1500 words; the official cap was not retrievable, treat as soft).
- Video (target ≤3 min; same).
- Cover image and media gallery.

### 0.3 Judging axes
Three axes — Impact, Technical Execution, Communication. Specific weights are not published; treat as roughly equal with an Impact tilt. Judges punish ambiguous targeting and reward "one user, one workflow, real bench" specificity.

### 0.4 Sponsor prizes (verified)
- **Unsloth Prize — $10,000** for best fine-tune. CircuitSage's fault-diagnosis LoRA is the route.
- *No other sponsor prizes confirmed for Gemma 4* (Ollama / Google AI Edge / NVIDIA Jetson / Cactus / MediaPipe were 3n-era, not Gemma 4). Do not promise these in the writeup.

### 0.5 Model variants (verified)
Gemma 4 family is **E2B**, **E4B** (edge variants — multimodal, function-calling), **26B-A4B** (MoE), **31B** (dense). There is **no "Gemma 4 27B"**. Gemma 3n is a prior model; do not reference it as Gemma 4. CircuitSage standardizes on:

- **Server inference (Ollama):** Gemma 4 **E4B** (`gemma4:4b-e4b` — verify exact tag at run time; if not yet on Ollama, hold at `gemma3:4b` and switch the moment the official tag publishes).
- **Fine-tune base (Unsloth):** Gemma 4 **E2B** (smaller; fits Kaggle's free T4; more training iterations per hour). Adapter targets the same family at inference time via Ollama Modelfile.
- **On-device (iOS / Android):** Gemma 4 **E2B** quantized.

When Codex runs P1 (dataset rebuild), use Gemma 4 E4B via Ollama for paraphrase augmentation if available; else gemma3:4b. Document the source on every row.

### 0.6 Native function calling
Gemma 4 supports native function calling. The patch's P4 (iterative agent loop) is on the critical path — once it lands, it should use the *native* tool-calling format that Gemma 4 emits natively, not a hand-rolled JSON-in-text shim.

---

## 1. Operating rules

Carry over from `WINNING_BUILD_PLAN.md` Section 0. Additions for this phase:

1. **Demo-first.** If a feature can't be shown in 3 minutes of video, deprioritize.
2. **Visible craft.** Frontend animations, sound design, and motion details matter on video. Spend taste on them.
3. **Offline-first is the differentiator.** Every feature must work with no internet on a fresh laptop. If a feature needs the cloud, it doesn't ship.
4. **Two-track narrative.** Every demo flow must work for the on-device iOS path *and* the LAN microserver path. Do not bake either into a single demo.
5. **No fake polish.** Do not claim accessibility, localization, on-device inference, or fine-tune quality unless you can demonstrate them. Judges sniff this out.

---

## 2. Sprint plan (overview)

Treat as advisory. Codex re-plans each day from `docs/BLOCKERS.md`.

| Day | Focus |
|---|---|
| Day 1 (after patch) | Phase 4.A — iOS on-device pilot (Cactus or `expo-llm-mediapipe`) |
| Day 2 | Phase 4.A finish + Phase 4.B fallback decision |
| Day 3 | Phase 5 — voice on iOS, native fn-calling on backend |
| Day 4 | Phase 6 — frontend split + motion polish |
| Day 5 | Killer feature K1 — schematic-to-netlist via Gemma 4 vision |
| Day 6 | Killer features K2–K3 — FFT waveform compare + lab-report PDF |
| Day 7 | Killer features K4–K5 — datasheet RAG, fault gallery, accessibility |
| Day 8 | Localization, hosted demo, polish, dry-run video shoot |
| Day 9 | Phase 7 — writeup, video, cover image (USER ACTIONs) |
| Day 10 | Buffer + submission |

---

## 3. Phase 4 — On-device inference path

**Goal:** make the iOS bench app run Gemma 4 with no internet on a real iPhone. The video will lean on this for ~30 seconds.

### Task 4.1 — Pick the bridge

Order of preference, fall through fast:

- **A.** `cactus-react-native` (Cactus). Verify package availability and Gemma 4 E2B compatibility.
- **B.** `expo-llm-mediapipe` (community wrapper around Google's MediaPipe LLM Inference). Confirms the gemma4 `.task` bundle path.
- **C.** Custom React Native binding around `llama.rn` (llama.cpp) loading a Gemma 4 E2B `.gguf`.
- **D.** Standalone Android Studio Kotlin app using MediaPipe LLM Inference (lose the iOS demo, but at least one on-device path ships).

If A and B both fail to install on the run machine, log to BLOCKERS and ship D in parallel.

**Files**
- modify `apps/ios/package.json`
- create `apps/ios/src/onDevice/Engine.ts`
- create `apps/ios/src/onDevice/types.ts`
- modify `apps/ios/App.tsx`
- create `apps/ios/assets/models/README.md` (instructions; **USER ACTION** to drop the actual `.task` or `.gguf` file)

### Task 4.2 — Engine interface

`Engine.ts` exposes:

```ts
export interface OnDeviceEngine {
  ready(): Promise<boolean>;
  modelInfo(): Promise<{ name: string; quant: string; sizeMB: number }>;
  diagnose(input: { question: string; measurements: Measurement[]; image_b64?: string }): Promise<StructuredDiagnosis>;
  cancel(): void;
}
```

Two implementations: `CactusEngine` and `MediaPipeEngine`. Both take a small wrapper prompt and call into the native bridge. The Bench UI's existing "Server (LAN)" path stays intact; users get a switch.

### Task 4.3 — Demo continuity

When local mode is on, the response shape must match the server's structured-diagnosis schema 1:1. Otherwise the existing UI breaks. If the on-device model produces JSON-shaped output reliably (Gemma 4 E2B does), use it directly; otherwise wrap the response with a tiny on-device "structurize" pass using the same model.

### Acceptance
- Toggle `Local model (offline)`, switch the iPhone to airplane mode, ask: *"My inverting op-amp is stuck near +12 V. What should I check?"* → returns a structured diagnosis with at least one likely fault and a next measurement, in ≤ 30 s on iPhone 14+.
- `apps/ios/README.md` documents the model bundling step.

### Killer demo moment
The video shows the iPhone's airplane-mode toggle visible in the status bar while CircuitSage answers. Practice this beat.

---

## 4. Phase 5 — Voice + Native function calling

### Task 5.1 — Voice in/out on iOS

**Files**
- modify `apps/ios/App.tsx`
- create `apps/ios/src/voice/{Recorder,Player,types}.ts`

**Spec**
- Hold-to-record button. Use `expo-speech-recognition` (or `react-native-voice` if Expo unsupported). System STT first; fall back to whispering audio bytes to the backend if STT fails.
- Auto-play answer via `expo-speech` TTS.
- Persist recordings to the session as artifacts when a session is selected.
- Long-press the mic for "narrate the screen" mode (reads the most recent diagnosis aloud).

**Acceptance**
- On a physical iPhone in a quiet room, hold mic, ask a 5-second question, see the text appear, get a spoken answer back. Works in airplane mode when local model is on.

### Task 5.2 — Native Gemma 4 function calling on the backend

**Files**
- modify `backend/app/services/agent_orchestrator.py`
- modify `backend/app/services/tool_runner.py` (created in patch P4)
- modify `backend/app/services/prompt_templates.py`

**Spec**
- Stop hand-rolling JSON tool-call parsing. Use Ollama's `tools` parameter with the Gemma 4-native function-calling format. Tool calls come back in `message.tool_calls[].function.{name, arguments}` shape; arguments are pre-parsed JSON.
- Add tool error pathways: any `run_tool(...)` exception → `{"error": str(exc)}` returned to the model so it can recover.
- Add a `final_answer` tool whose schema matches the structured-diagnosis JSON. The agent loop terminates when the model calls `final_answer` (cleaner than parsing free text).
- Keep iteration cap at 4. Add a 30 s wall-clock budget per loop.

**Acceptance**
- Live test (Ollama up): `POST /api/sessions/seed/op-amp` records 2–4 tool calls and ends with a `final_answer` event. `gemma_status: ollama_gemma_agentic`.

---

## 5. Phase 6 — Frontend rewrite, motion, accessibility

### Task 6.1 — Split single-file frontend

`frontend/src/main.tsx` must end up under 100 lines (router shell only). Move:

```
frontend/src/
  App.tsx
  routes/
    Home.tsx
    Studio.tsx
    Bench.tsx
    Companion.tsx
    Educator.tsx        # new (see K6)
    Faults.tsx          # new (see K7)
  components/
    DiagnosisCard.tsx
    FaultRanking.tsx
    EvidenceStrip.tsx
    ToolTimeline.tsx
    ChatPanel.tsx
    GemmaStatusBanner.tsx
    OfflineBadge.tsx
    SchematicPreview.tsx
    WaveformPlot.tsx
    MeasurementForm.tsx
    UploadPanel.tsx
    QrPanel.tsx
    LanguageSwitcher.tsx
  hooks/
    useSession.ts
    useGemmaHealth.ts
    useChat.ts
    useI18n.ts
  lib/
    api.ts
    types.ts
    format.ts
    a11y.ts
```

Each file ≤ 400 lines. Add `wouter` for typed routing.

### Task 6.2 — Motion + sound design

**Files**
- add `framer-motion`
- create `frontend/src/components/Motion/*.tsx`
- create `frontend/src/lib/sounds.ts` (use Web Audio API; no external assets)

**Spec**
- Diagnosis card slides in with a 200 ms ease-out; the fault-confidence bar fills with a 600 ms cubic.
- The "next measurement" pill pulses once.
- Tool-timeline events stream in left-to-right with 80 ms stagger.
- Sound: a soft "tick" when a tool call completes; a single "chime" when a diagnosis finishes; opt-out toggle in the top right. Generated procedurally with Web Audio (no audio files).
- Reduce-motion media query honored throughout.

### Task 6.3 — Accessibility

Aligns with **Digital Equity & Inclusivity** track. Implement:

- Full keyboard nav across Studio, Bench, Companion routes (visible focus rings, Tab order, Esc closes modals).
- ARIA live region for `gemma_status` changes.
- Alt text on every QR, scope, and breadboard image.
- Color-blind palette: avoid red/green-only signals; use shape + text labels too.
- High-contrast mode toggle (CSS variables flipped).
- Large-font mode toggle (root `font-size: 18px → 22px` and proportional spacing).
- All form inputs have associated labels and error messages.

### Task 6.4 — Localization (i18n)

**Files**
- create `frontend/src/i18n/{en,hi,es,pt}.ts`
- create `frontend/src/hooks/useI18n.ts`

**Spec**
- 4 locales: English, Hindi, Spanish, Portuguese. Translations cover UI strings only (~80 keys).
- `useI18n()` reads `navigator.language` for default, persists override to `localStorage`.
- Backend system prompt picks up the requested language via a `lang` field on chat / diagnose requests; the LLM is instructed to reply in that language. Structured JSON keys stay English; only `student_explanation`, `next_measurement.instruction`, and `safety.warnings` translate.
- **USER ACTION**: have a fluent speaker review Hindi and Portuguese before submission.

### Acceptance
- `npm --prefix frontend run build` exits 0 with all routes intact.
- Screen-reader walkthrough of Studio reads in coherent order (manual; document in `docs/ACCESSIBILITY.md`).
- Hindi locale renders without layout breakage; right-to-left not required.

---

## 6. Killer features (priority-ordered)

These are the pieces that turn a competent submission into a memorable one. Each is independent; ship in priority order.

### K1 — Schematic-to-netlist via Gemma 4 vision (highest ROI)

**Why judges care:** This is the demo's "wow" moment. A student photographs a hand-drawn schematic; CircuitSage produces a SPICE netlist; the existing pipeline takes over. No other entry will do this.

**Files**
- create `backend/app/tools/schematic_to_netlist.py`
- create `backend/app/services/netlist_validator.py`
- modify `backend/app/main.py` (new endpoint `POST /api/tools/schematic-to-netlist`)
- modify `backend/app/services/agent_orchestrator.py` (auto-run on freshly uploaded schematic images when no netlist exists)

**Spec**
- One Gemma 4 vision call with the schematic image and a tightly scoped prompt:
  ```
  You are a circuit-recognition assistant. Convert the visible schematic
  to a minimal SPICE netlist with these rules:
  - Use refs Rin / Rf / R1..Rn / C1..Cn / Q1..Qn / D1..Dn etc.
  - Use nodes vin, vout, n_inv, n_noninv, vcc, vee, gnd (alias 0).
  - Use SI suffixes: k, meg, n, u.
  - Skip components you cannot see clearly.
  Return JSON: {"netlist": "...", "confidence": 0..1, "missing": ["..."]}
  ```
- Validate the returned netlist by piping it through `parse_netlist_text`. If `detected_topology == "unknown"`, return `confidence: low` and a `needed: [...]` list.
- The Studio UI gains a "Recognize from photo" button on every uploaded schematic image. Click → preview the inferred netlist → user accepts → it becomes a real `netlist` artifact and triggers diagnosis.

**Acceptance**
- Upload a hand-drawn op-amp inverting schematic photo → recognized netlist matches the existing canonical netlist within ±1 component.
- Live test on a deliberately ambiguous photo returns `confidence: low` with a non-empty `missing` field instead of fabricating components.

**Demo moment:** in the video, the student sketches a circuit on paper, photographs it, watches the netlist appear, runs diagnosis. ~20 seconds of pure narrative gold.

### K2 — Live oscilloscope mode

**Why judges care:** real-time evidence ingestion makes the system feel alive on video.

**Files**
- create `backend/app/services/streaming.py`
- create new endpoint `POST /api/sessions/{id}/measurements/stream` (SSE)
- modify `frontend/src/routes/Studio.tsx` (new "Live" panel)

**Spec**
- The bench app or a desktop CLI can POST measurements at up to 5 Hz.
- The backend keeps a rolling 60-second window per session.
- Drift detection: if a measured value's standard deviation over the last 10 s exceeds the expected (per topology), trigger a "drift" event into the diagnosis tool calls.
- Studio's Live panel shows a sparkline per measurement label.

**Acceptance**
- Run `python scripts/synth_stream.py --label Vout --pattern intermittent` and watch a sparkline animate; the diagnosis ranks `intermittent_connection` higher.

### K3 — FFT waveform comparison

**Why judges care:** moves beyond saturation detection to harmonic distortion (a real bench skill).

**Files**
- modify `backend/app/tools/waveform_analysis.py`
- create `backend/tests/test_waveform_fft.py`

**Spec**
- Add `fft_analysis(times, values)` returning fundamental frequency, top 5 harmonics, THD %, and a confidence level.
- Add `compare_waveform_spectra(expected_csv, observed_csv)` that classifies the mismatch as one of: clipping, harmonic distortion, frequency drift, missing fundamental, noise floor too high.
- Wire into `compare_expected_vs_observed`.

**Acceptance**
- Synthetic test: 1 kHz sine + clipping → reports clipping with confidence > 0.8 and second/third harmonic energies.
- 1 kHz sine + 10 % third-harmonic → reports harmonic distortion.
- Pure 950 Hz vs expected 1 kHz → reports frequency drift.

### K4 — Lab-report PDF export with embedded SVG schematic

**Why judges care:** real artifact a student can hand to an instructor; closes the loop end-to-end.

**Files**
- modify `backend/app/tools/report_builder.py`
- create `backend/app/tools/schematic_renderer.py`
- modify `backend/requirements.txt` (`weasyprint>=63` or `reportlab>=4`)
- new endpoint `GET /api/sessions/{id}/report.pdf`

**Spec**
- `schematic_renderer.py` takes a parsed netlist and emits a tidy SVG (per-topology layouts: op-amp inverting/non-inverting, RC, divider, BJT, rectifier). Use a small library of pre-drawn SVG component glyphs.
- `report_builder.py` produces an HTML report; WeasyPrint renders to PDF.
- Include: cover page (session title, student level, date), aim, expected behavior (with computed values), observed behavior (with measurements table), diagnosis (top fault + why + verification test), corrected concept, simulation-vs-hardware section, viva questions, schematic SVG, scope before/after thumbnails.

**Acceptance**
- `curl -OJ localhost:8000/api/sessions/<id>/report.pdf` produces a 2–4 page PDF that opens cleanly in Preview.

### K5 — Component datasheet RAG with part-number lookup

**Files**
- expand `backend/app/knowledge/datasheets/` to 20+ parts (op-amps, BJTs, MOSFETs, diodes, regulators, timers, common ICs).
- create `backend/app/tools/datasheet.py`
- new endpoint `GET /api/datasheets/{partnumber}`

**Spec**
- The agent gets a `lookup_datasheet(part_number)` tool. Returns pin map, abs max, typical use, common faults.
- Studio surfaces a small "datasheet" badge wherever a ref (e.g., Q1 = 2N3904) is recognized in a netlist.

**Acceptance**
- Upload a netlist with `Q1 ... 2N3904` → datasheet badge appears → click → shows pinout + abs-max + common faults.

### K6 — Educator dashboard

**Why judges care:** Future of Education is the primary track; instructor scaling is the original problem statement. Showing it directly aligns the writeup.

**Files**
- create `frontend/src/routes/Educator.tsx`
- new endpoint `GET /api/educator/overview`

**Spec**
- Read-only route at `/educator`.
- Aggregations across sessions: most common fault per topology, average time-to-resolution, count of safety refusals, count of unfinished sessions.
- A small histogram of where students get stuck (which measurement they stalled on).
- No PII; sessions are anonymous IDs.

**Acceptance**
- Seed three demo sessions with different faults; the dashboard renders the aggregates correctly.

### K7 — Faults gallery

**Files**
- create `frontend/src/routes/Faults.tsx`
- create `backend/app/main.py` endpoint `GET /api/faults` returning the catalog flat.

**Spec**
- A page listing every catalog fault grouped by topology. Each fault card shows: name, why, requires_measurements, verification_test, fix_recipe, an inline scope-before/scope-after thumbnail (use existing `sample_data` placeholders), and a "try this fault" button that seeds a session pre-loaded with that scenario.

**Acceptance**
- Open `/faults` → see ≥ 18 fault cards across 6 topologies → click "try this fault" → land in Studio with a session ready to diagnose.

### K8 — Topology pack expansion

**Why judges care:** breadth signals real engineering. Currently 6 topologies. Add 4–6 more.

Add catalogs and detection for:
- Active high-pass filter (op-amp + R + C feedback).
- Op-amp integrator and differentiator.
- Schmitt trigger (positive feedback).
- 555 timer astable.
- N-MOSFET low-side switch with gate-drive.
- Instrumentation amplifier (3-op-amp).

For each: fault catalog JSON, sample data, parser detection, three sample faults.

**Acceptance**
- Each new topology has a working seed endpoint and at least one non-canned diagnosis.

### K9 — Hugging Face dataset card + LoRA model card

**Files**
- `train/dataset/card.md` (HF dataset card)
- `train/output/MODEL_CARD.md` (HF model card)

**Spec**
- After P1's dataset rebuild, publish to Hugging Face under `karanbishtt/circuitsage-faults-v1`. Include: data construction methodology, distribution table, licensing (MIT, all data original), known biases, intended use.
- Model card mirrors the dataset card and adds: base model (Gemma 4 E2B), LoRA hyperparameters, training compute, eval results on a held-out 200-example test set.
- **USER ACTION**: HF account + token. Codex prepares everything else.

**Acceptance**
- Both cards exist in the repo and are syntactically valid HF metadata YAML at the top.

### K10 — Hosted demo

**Why judges care:** judges want to click a link.

**Files**
- create `Dockerfile`
- create `fly.toml` (or `railway.toml`)
- create `docs/DEPLOYMENT.md`

**Spec**
- One container: backend + Ollama (run `ollama serve` as a sidecar; pull `gemma3:4b` at boot if disk allows; otherwise document a smaller model).
- Frontend on Vercel / Cloudflare Pages, pointed at `https://circuitsage-api.fly.dev`.
- The hosted demo is read-only from the public's perspective: rate-limit measurements/diagnose calls per IP. Bench Mode and Companion are local-LAN-only and stay disabled in the hosted build.
- **USER ACTION**: Fly account, deploy keys.

**Acceptance**
- A judge clicks the URL, lands on Studio, runs the op-amp seed, gets a real diagnosis. Latency < 5 s for the first call once warm.

### K11 — Failure-mode gallery (uncertainty calibration)

**Why judges care:** Safety & Trust track. Showing where the system *says no* is rare and impressive.

**Files**
- modify `frontend/src/routes/Faults.tsx` (gain a "When CircuitSage says no" tab)
- create `sample_data/uncertainty/` with 6–10 example sessions where the catalog returns `confidence: low` and asks for more evidence.

**Spec**
- Each example shows: the input, what was missing, what the system asked for, and what a correctly diagnosed version of the same circuit would have looked like.

**Acceptance**
- 6+ uncertainty examples viewable; the writeup quotes one of them.

### K12 — Hardware demo helper

**File**
- create `docs/HARDWARE_BENCH.md`

**Spec**
- Cheat-sheet for the demo bench: BOM (op-amp TL081, two resistors, a 9 V battery clip, two 9 V batteries, a function generator or 555 oscillator, a USB scope), wiring diagram, common things to mess up *on purpose* for the video, retake guide.
- Camera and lighting suggestions for a clean iPhone-shot demo.

**Acceptance**
- A hobbyist can replicate the demo bench in under an hour.

---

## 7. Quality engineering

### Q1 — Integration tests
**File:** `backend/tests/integration/test_demo_flows.py`. Cover all 6+ topology seed endpoints end-to-end (create → upload → measure → diagnose → report). Run in CI.

### Q2 — End-to-end demo smoke
**File:** `scripts/demo_smoke.sh`. Boots backend, hits each seed, asserts the structured-diagnosis schema, prints a green/red status line. The video shoot script invokes this before each take.

### Q3 — Eval harness for the LoRA
**File:** `train/eval/harness.py`. Feeds a 200-example held-out test set through the loaded `circuitsage:latest` model and computes: schema-validity rate, exact-match on `experiment_type`, top-1 fault-id match, safety-refusal precision/recall. Stored as `train/eval/last_run.json`.

### Q4 — CI matrix
**File:** `.github/workflows/ci.yml`. Jobs: backend pytest (3.12), frontend tsc + build, desktop check, ios `expo-doctor`. Cache pip + npm.

### Q5 — Telemetry (opt-in only)
**File:** `backend/app/services/telemetry.py`. If `CIRCUITSAGE_TELEMETRY=on` (default off), append-only JSONL of events: topology, fault id, time-to-resolution, gemma_status. Used to populate the Educator dashboard. Fully local; never leaves the host.

---

## 8. Phase 7 — Submission materials

### S1 — Video script
**File:** `docs/DEMO_SCRIPT.md` (rewrite; the existing version is the v1 stub).

3-minute structure:
- 0:00–0:18 — Hook. *"Software students get stack traces. Electronics students get silence."* Show a flat oscilloscope and a frustrated student.
- 0:18–0:42 — Tour the Studio. Load the op-amp seed; show simulation, measurements, tool calls.
- 0:42–1:05 — Bench Mode. QR pairing on the iPhone. Snap the breadboard photo. Schematic-to-netlist (K1) does its thing.
- 1:05–1:35 — **Airplane-mode beat.** Visible airplane-mode toggle. The iPhone runs the diagnosis on-device with Gemma 4 E2B. Voice in/out. The fault is identified.
- 1:35–2:10 — The fix. The student grounds the non-inverting input. Live oscilloscope mode (K2) shows the waveform return to expected. Confidence chip flips to high.
- 2:10–2:35 — Lab report PDF (K4) generates. Slide through pages.
- 2:35–2:55 — Educator dashboard (K6) shows three students hitting the same fault — the system flags it as a class-wide misconception.
- 2:55–3:00 — Closing card: "CircuitSage. Stack traces for circuits."

**USER ACTION**: actually shoot it.

### S2 — Writeup
**File:** `docs/KAGGLE_WRITEUP_DRAFT.md` (rewrite).
Sections: Problem (silent failures + bench mentorship gap), Solution (the workflow), Tracks (Education + Equity + Safety), Architecture (microserver + on-device), Multimodal (vision + voice), Fine-tune (Unsloth + dataset card), Reproducibility (`make install && make demo`), Safety (refusal + uncertainty calibration), Limitations, Future Work.
Target ≤ 1500 words.

### S3 — Cover image + gallery
**Files:** `docs/MEDIA_GALLERY.md`, `media/cover.png` (1600×900).
Codex generates the layout in HTML + the existing dark theme; **USER ACTION** screenshots from a polished build.

---

## 9. Submission-day sign-off checklist

Before tagging `v1.0.0-submission`:

- [ ] `make install && make demo` works on a fresh clone in < 5 min.
- [ ] All 12 topology seed endpoints (6 + 6 from K8) return non-canned diagnoses.
- [ ] Schematic-to-netlist (K1) recognizes the canonical op-amp photo within ±1 component.
- [ ] iPhone in airplane mode answers a question via on-device Gemma 4 in ≤ 30 s.
- [ ] Voice in/out works on iOS (Phase 5).
- [ ] LoRA `circuitsage:latest` is loaded; `gemma_model` reports it.
- [ ] LoRA eval harness (Q3) reports schema-validity ≥ 95 %, top-1 fault-id ≥ 60 %.
- [ ] Hosted demo URL serves the op-amp seed in < 5 s.
- [ ] PDF lab report renders cleanly.
- [ ] Educator dashboard renders aggregates.
- [ ] Faults gallery shows ≥ 30 cards; uncertainty gallery shows ≥ 6 cases.
- [ ] Hindi, Spanish, Portuguese locales render without layout breakage.
- [ ] Accessibility audit passes (manual screen-reader walkthrough; high-contrast mode toggle works).
- [ ] CI green on the submission commit.
- [ ] Video script printed; bench BOM ready.
- [ ] Writeup ≤ 1500 words; cover image rendered.
- [ ] HF dataset card + model card uploaded (K9).
- [ ] No `console.log` / `print` debug statements; no hardcoded secrets.
- [ ] Tag: `git tag v1.0.0-submission && git push --tags`.
- [ ] Submitted on Kaggle with repo URL, video URL, writeup URL.

---

## 10. Cut lines (when running short on time)

Reverse priority — drop in this order:

1. K12 hardware demo helper.
2. K11 uncertainty gallery as a separate route (fold into K7).
3. K8 topology pack down to 2 new topologies (Schmitt + 555).
4. K10 hosted demo (LAN-only is acceptable; provide a Vagrant box instead).
5. Phase 5.1 voice (text mode is acceptable).
6. K9 HF cards (keep the model+dataset local).
7. Localization down to en + hi only.
8. Phase 4.A on-device iOS — fall back to Phase 4.B Android only.
9. K2 live oscilloscope.
10. K3 FFT distortion analysis.

Never cut: P1 dataset rebuild, P4 agent loop, K1 schematic-to-netlist, K4 PDF report, Phase 6.3 accessibility, Phase 6.4 i18n (en + 1 other), Phase 7 video + writeup, sign-off checklist verifications.

---

## 11. Tactical notes for Codex

- **Verify model tags at run time, not from this doc.** Hit `https://ollama.com/library/gemma4` and the Hugging Face Unsloth Gemma 4 collection. Pin the exact tag/id you see; do not invent.
- **The patch's P1 (dataset rebuild) is the highest-value single block of work in the entire forward plan.** A real LoRA on a real dataset is the Unsloth Prize lane and the Technical Execution lift. Spend the time.
- **Spend taste on the frontend.** Two evenings of motion polish (Phase 6.2) and accessibility (Phase 6.3) move the Communication score more than two days of new features.
- **The video is the artifact.** If a feature can't fit in 3 minutes, it doesn't exist for judging. Measure every feature against the video script before building it.
- **Anti-pattern alert (again).** No silent fallbacks. Every status the user sees must be honest. The audit caught one fake-data instance; do not introduce another.
- **Commit cadence.** After every numbered task or killer feature, commit with `circuitsage: forward.<id> <summary>`.
- **Ask, don't invent.** USER ACTION items: video shoot, training compute, signing certs, HF account. Stub them in code, surface them in `docs/BLOCKERS.md`, do not fake.

End of plan.
