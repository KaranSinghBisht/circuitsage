# Phase 3.5 follow-up + winning-grade hardening

**Audience:** the same Codex agent that ran `WINNING_BUILD_PLAN.md` Phases 0–3, then `PHASE_3_5_PATCH.md`, then `WINNING_FORWARD_PLAN.md` through K10.
**Read order:** this doc *first*, before any further forward-plan work.
**Time budget:** 8–12 hours single autonomous run. The doc is structured so partial completion still ships value.
**Why this exists:** an anti-slop reviewer pass found 7 small cleanup items and several high-leverage gaps that Codex skipped at cut-lines. This doc closes them, then keeps Codex grinding on judge-visible polish until time runs out.

Operating rules from `WINNING_BUILD_PLAN.md` Section 0 carry over (phase order, acceptance gates, BLOCKERS log, no silent fallbacks, commit after each item: `git add -A && git commit -m "circuitsage: harden.<id> <summary>"`).

This doc has 6 groups (A–F). Within each group, items run in order and have their own acceptance. Do NOT skip groups.

---

## 0. Pre-flight (run once before Group A)

```bash
git status                          # must be clean
make test                           # baseline; should pass
backend/.venv/bin/python train/dataset/validate.py
ls backend/app/services/fault_data/ | wc -l   # expect 13
```

If any pre-flight fails, log to `docs/BLOCKERS.md` and stop.

---

## Group A — Reviewer cleanup (~1 hour)

### A1 — Pin numpy explicitly
**Why:** `backend/app/tools/waveform_analysis.py` imports `numpy` but `backend/requirements.txt` doesn't list it. Today numpy comes in transitively via chromadb; if those deps shift, FFT analysis silently fails.

**Files:** `backend/requirements.txt`.

**Spec:** add `numpy>=2.0,<3` on its own line. Re-run `pip install -r backend/requirements.txt` to confirm resolution.

**Acceptance:** `pip show numpy` reports an installed version; `make test` still passes.

### A2 — Quarantine the schematic hint-fallback
**Why:** `recognize_schematic_sync_fallback` in `backend/app/tools/schematic_to_netlist.py` returns a hardcoded canonical op-amp netlist when text contains `"opamp"`. Even tagged `mode: hint_fallback`, this can be misread as recognition success in demos.

**Files:** `backend/app/tools/schematic_to_netlist.py`, callers, `backend/tests/test_schematic_to_netlist.py`.

**Spec:**
- Rename `recognize_schematic_sync_fallback` to `_demo_seed_op_amp_netlist` and mark it private.
- Move it from `tools/` to `backend/app/services/demo_seeds.py` (create that file). It exists *only* for the op-amp seed endpoint.
- The schematic-recognition pipeline (`recognize_schematic`) must NOT call it. If vision fails, return `{"mode": "vision_unavailable", "netlist": "", "confidence": 0.0, "missing": [...]}` — no fabrication.
- Update tests: keep the `op-amp seed netlist parses to gain -4.7` assertion in a renamed test that imports from `demo_seeds.py`. Remove any assertion that the public schematic API returns a hardcoded netlist for hint text.

**Acceptance:**
- `grep -r "recognize_schematic_sync_fallback" backend frontend` returns nothing.
- `pytest backend/tests/test_schematic_to_netlist.py` passes.
- Op-amp seed endpoint still produces a working session.

### A3 — Add `.github/workflows/ci.yml`
**Why:** Q4 in the forward plan. Submission must land green.

**Files:** create `.github/workflows/ci.yml`.

**Spec:** one workflow, three jobs, all on push and on PR to any branch:
1. `backend` — Ubuntu, Python 3.12, cache pip, `pip install -r backend/requirements.txt`, `PYTHONPATH=backend pytest backend/tests -q`.
2. `frontend` — Ubuntu, Node 22, cache npm, `npm --prefix frontend ci`, `npm --prefix frontend run build`, `npm --prefix apps/desktop ci`, `npm --prefix apps/desktop run check`.
3. `dataset` — Ubuntu, Python 3.12, `python train/dataset/validate.py`.

Skip iOS (Expo) in CI; document in the workflow comment that iOS is verified locally with `npx expo install --check`.

**Acceptance:** push a branch, CI runs all three jobs green. If GitHub Actions is offline locally (it is), validate the YAML with `actionlint` if available, otherwise log to BLOCKERS but commit the file.

### A4 — i18n coverage sweep
**Why:** four locales × 29 keys is suspiciously sparse; some user-visible strings are likely still English-only.

**Files:** `frontend/src/i18n/{en,hi,es,pt}.ts`, route + component files.

**Spec:**
1. Run `grep -hPoE '">[A-Z][^<]{6,}<"|"[A-Z][^"]{8,}"' frontend/src/{routes,components}/*.tsx | sort -u > /tmp/strings.txt` (or equivalent). Strip false positives (URLs, paths, code).
2. For each unique string not currently keyed in `en.ts`, add a key.
3. Translate the additions into hi, es, pt. Use clear domain-appropriate translations; do NOT machine-translate technical terms like "non-inverting input" verbatim — keep them English-prefixed if there is no clean target-language equivalent.
4. Wire `useI18n()` into every component that previously had hardcoded English.
5. Add a CI lint: `python scripts/i18n_check.py` walks the four locale files and asserts they all have the same keys; exits non-zero on mismatch. Wire into the `frontend` CI job.

**Acceptance:** `wc -l frontend/src/i18n/*.ts` shows ≥ 60 lines per locale. `python scripts/i18n_check.py` exits 0.

### A5 — Verify topology-pack test coverage
**Files:** read `backend/tests/test_topology_pack.py`; extend if needed.

**Spec:** ensure every one of the 13 topologies has a test that:
- POSTs to `/api/sessions/seed/<topology>` (or equivalent).
- Asserts the resulting diagnosis returns at least one fault from that topology's catalog by `id`.
- Asserts `gemma_status in {"deterministic_fallback", "ollama_gemma_agentic", "ollama_gemma_single_shot"}`.
- Asserts `experiment_type == <topology>`.

If any topology lacks a seed endpoint, add it (mirror the op-amp seed shape).

**Acceptance:** `pytest backend/tests/test_topology_pack.py -v` shows 13 passing test names, one per topology.

### A6 — Submission checklist as a tracked file
**Why:** Section 9 of the forward plan was in-doc; on submission day it needs to be a runnable checklist, not buried.

**Files:** create `docs/SUBMISSION_CHECKLIST.md`.

**Spec:** lift Section 9 of `WINNING_FORWARD_PLAN.md` verbatim. Add a "Status" column with `[ ]` markers. Add a "Last verified at HEAD" line at the bottom that Codex updates after each `make test` pass.

**Acceptance:** file exists, lints as valid markdown, has 24+ checklist items.

### A7 — FastAPI lifespan migration
**Why:** `on_event("startup")` deprecation warning shows up on every test run; small but visible to a judge running tests.

**Files:** `backend/app/main.py`.

**Spec:** replace the `@app.on_event("startup")` block with `@asynccontextmanager` lifespan handler attached via `FastAPI(lifespan=lifespan)`. Behavior identical: call `init_db()` at startup.

**Acceptance:** `make test` runs with **zero** deprecation warnings.

---

## Group B — Knowledge & datasheet expansion (~2 hours)

### B1 — Expand the textbook corpus
**Why:** RAG only has 5 textbook files. The new K8 topologies (active high-pass, integrator, differentiator, Schmitt, 555, MOSFET, instrumentation amp) have no corpus content, so retrieval for those topologies is weak.

**Files:** `backend/app/knowledge/textbook/{active_highpass.md, op_amp_integrator.md, op_amp_differentiator.md, schmitt_trigger.md, timer_555.md, mosfet_switch.md, instrumentation_amp.md}` — 7 new files.

**Spec:** each file is **original** content (rule from `SOURCES.md`: no external copy), 250–500 lines, structured: theory, transfer function / formula, expected behavior, common faults (cite the catalog ids), how to measure key nodes. Write tightly; do not pad.

**Acceptance:** `wc -l backend/app/knowledge/textbook/*.md` shows ≥ 250 lines per new file. Re-run `python scripts/ingest_corpus.py`. RAG query for `"schmitt trigger hysteresis"` returns the new file in the top-2.

### B2 — Datasheet expansion
**Why:** the datasheet RAG has 5 parts. Real-world circuits use many more.

**Files:** `backend/app/knowledge/datasheets/{TL072.md, LM358.md, NE5532.md, LF356.md, LM317.md, 7805.md, 7905.md, 1N4007.md, 1N5819.md, 2N7000.md, IRF540N.md, BC547.md, BC557.md, 2N2222.md, MCP6002.md}` — 15 new datasheet briefs.

**Spec:** each is original ≤ 80 lines covering: package + pin map (text only, no ASCII art beyond a 6-line diagram), absolute max ratings, typical operating point, common application, common faults. Same SOURCES.md provenance rule.

**Acceptance:** `ls backend/app/knowledge/datasheets/*.md | wc -l` ≥ 20. The datasheet endpoint `GET /api/datasheets/TL072` returns structured content.

### B3 — Datasheet auto-detect from netlist refs
**Files:** `backend/app/services/agent_orchestrator.py`, `backend/app/tools/datasheet.py`.

**Spec:** when the parsed netlist has components with model strings (Q1 model `2N3904`, D1 model `1N4148`, etc.), automatically run `datasheet.lookup(part)` for each unique part and feed the result into the LLM context. Cap at 3 datasheets per diagnosis to bound prompt length.

**Acceptance:** new test: a netlist containing `Q1 ... 2N3904` and `D1 ... 1N4148` produces `tool_calls` entries for both datasheet lookups.

---

## Group C — LoRA eval harness, integration tests, demo data (~2 hours)

### C1 — LoRA evaluation harness
**Why:** Q3 in the forward plan. Without it, the Unsloth Prize writeup has no metrics.

**Files:** create `train/eval/{harness.py, eval_set.jsonl}`, `train/eval/README.md`.

**Spec:**
- Hold-out 200 examples from `train/dataset/circuitsage_qa.jsonl` (deterministic seed: take every 30th row before any further mutation).
- `harness.py` accepts `--model <ollama-tag>` and runs each example, comparing the model's output to the gold assistant content on:
  1. `schema_validity_rate` — fraction of outputs that are valid JSON matching the structured-diagnosis schema.
  2. `experiment_type_exact_match`.
  3. `top_fault_id_match` — fraction where `predicted.likely_faults[0].id == gold.likely_faults[0].id` (when gold has any).
  4. `safety_refusal_precision` and `safety_refusal_recall` against the 5% safety branch.
  5. `mean_latency_ms`.
- Persist results to `train/eval/runs/<timestamp>.json` and update `train/eval/last_run.json`.
- Print a summary table.

**Acceptance:**
- `train/eval/eval_set.jsonl` has 200 rows.
- `python train/eval/harness.py --model gemma3:4b` runs (Ollama needed; if down, log blocker but assert harness syntax is valid by importing it: `python -c "import train.eval.harness"`).
- The harness exits 0 with Ollama up and produces a metrics JSON.

### C2 — Integration tests across all 13 topologies
**Why:** Q1 in the forward plan; a single missing topology endpoint at submission time is catastrophic.

**Files:** create `backend/tests/integration/test_demo_flows.py`.

**Spec:**
- Parametrize over the 13 topology ids.
- Each test: create session via seed → assert at least one artifact exists → POST a measurement → POST diagnose → GET report → GET report.pdf → assert each step returns 2xx and the diagnosis has the topology's catalog top fault as one of `likely_faults`.

**Acceptance:** `pytest backend/tests/integration -v` shows 13 passing tests.

### C3 — Demo seed flow with synthetic Educator data
**Why:** the Educator dashboard exists but has no data on a fresh install. A judge clicking it sees an empty page.

**Files:** create `scripts/demo_seed.py`, `Makefile` target `demo-seed`.

**Spec:**
- Seed 8 sessions across topologies, including:
  - 3 successfully resolved op-amp inverting cases (varied measurements).
  - 2 unresolved RC low-pass cases (stuck waiting for next measurement).
  - 1 voltage divider with the load fault.
  - 1 BJT common-emitter with incorrect base bias.
  - 1 safety-refusal session.
- Each session has 2–4 measurements and a final diagnosis.
- Idempotent: running twice does not double-seed (use a session-id prefix `demo:` and clear it on re-run).

**Acceptance:** `make demo-seed` populates the DB. Visiting `/educator` after seed shows non-empty aggregations.

### C4 — Demo smoke script
**Files:** create `scripts/demo_smoke.sh`.

**Spec:** boots backend in background, hits each of the 13 seed endpoints + `/api/educator/overview` + `/api/sessions/<id>/report.pdf`, prints a green/red status line per endpoint, exits non-zero on any failure. Used as a pre-shoot check before the video.

**Acceptance:** `bash scripts/demo_smoke.sh` exits 0 on a fresh install (after `make demo-seed`).

---

## Group D — Failure-mode gallery, K11 (~2 hours)

### D1 — Backend uncertainty cases
**Why:** Safety & Trust track narrative. Showing where CircuitSage *says no* is rare and impressive.

**Files:** create `sample_data/uncertainty/<8 cases>/{netlist.net or note.txt, student_question.txt, expected_outcome.json}`.

**Spec:** 8 hand-curated cases where the system *should* return `confidence: low` and ask for more evidence rather than picking a fault. Examples:
1. Op-amp with no rails listed in the netlist.
2. RC filter with a missing capacitor (only resistor present).
3. Free-form question without any artifacts.
4. Two-gain conflicting student measurements (5 and 50 for the same node).
5. Photo of a breadboard but no schematic.
6. A netlist with a topology not in the catalog (e.g., a Wien bridge).
7. A measurement at the wrong unit (Ω instead of V).
8. A safety-edge case (low-voltage but mentions a battery in series with a wall-wart).

`expected_outcome.json` documents what CircuitSage *should* respond with, used as a regression test.

**Acceptance:** new test `backend/tests/test_uncertainty_gallery.py` parametrizes over the 8 cases and asserts `confidence == "low"` and `next_measurement.label != "Stop live debugging"` (unless safety-refusal expected).

### D2 — Frontend uncertainty route
**Files:** modify `frontend/src/routes/Faults.tsx` (or create `Uncertainty.tsx`); router entry.

**Spec:** new route `/uncertainty` lists the 8 cases as cards. Each card shows: input, what was missing, what the system asked for, and the `confidence: low` outcome. Linked from the Faults page.

**Acceptance:** `/uncertainty` route renders 8 cards; the build still passes.

---

## Group E — Submission polish (~1 hour)

### E1 — Demo script v2
**Files:** rewrite `docs/DEMO_SCRIPT.md`.

**Spec:** the Forward Plan section S1 had the 3-min cut. Promote it to the canonical script. Add: shot list per beat (camera angle, on-screen overlay text, voiceover line), B-roll list, retake guidance. Mark every `USER ACTION` beat (the actual filming) clearly.

**Acceptance:** file is ≥ 300 lines, contains a per-beat table, references the airplane-mode scene.

### E2 — Writeup v2
**Files:** rewrite `docs/KAGGLE_WRITEUP_DRAFT.md`.

**Spec:** ≤ 1500 words. Sections per Forward Plan S2. Include: the LoRA eval metrics from C1's last run (placeholder if Ollama is down), the failure-mode gallery (D2), the on-device airplane-mode story, and one explicit "limitation" paragraph (uncertainty calibration is the differentiator). Cite the repo, video, dataset card, and model card URLs (placeholders allowed).

**Acceptance:** word count is in `[1200, 1500]`. No filler. No "we are excited to" / "in this work we" boilerplate.

### E3 — README polish + screenshot script
**Files:** modify `README.md`; create `scripts/screenshots.md`.

**Spec:**
- README opens with tagline + one-paragraph pitch + a hero image link (`media/cover.png` placeholder).
- "Quickstart" stays at `make install && make demo`.
- New section "What's inside": bulleted list of every major capability with a one-line description and a route/endpoint where it lives.
- New section "Tracks": Future of Education, Digital Equity, Safety & Trust — one paragraph each tying back to features.
- New section "Reproducing the LoRA": pointers to `train/README.md`, dataset card, eval harness.
- `scripts/screenshots.md` is a step-by-step script for capturing the 8 screenshots judges will see (Studio, Bench, Companion, Educator, Faults, Uncertainty, PDF report, on-device iOS).

**Acceptance:** README is ≤ 250 lines, every link resolves to an existing file or a clearly marked placeholder.

### E4 — OpenAPI link + API docs route
**Files:** modify `backend/app/main.py` (FastAPI `docs_url` is already on `/docs`); add a small route map page.

**Spec:** add a `GET /api/routes` endpoint that returns a structured list of every public endpoint with method, path, and one-line description. Link it from the README under "API surface".

**Acceptance:** `curl localhost:8000/api/routes | jq 'length'` ≥ 25.

### E5 — HuggingFace cards (K9) — local-only artifacts
**Files:** create `train/dataset/card.md`, `train/output/MODEL_CARD.md`.

**Spec:** valid HuggingFace dataset and model card YAML frontmatter at the top, then prose. Dataset card: data construction, distribution table (re-run from `validate.py` output), licensing (MIT), known biases (synthetic; rule-based augmentation when Ollama is down), intended use. Model card: base model `unsloth/gemma-3-4b-it` (placeholder if Codex finds the published Gemma 4 Unsloth tag — verify before pinning), LoRA hyperparameters, eval metrics from C1's last run (placeholder when Ollama is down), intended use, ethical considerations, limitations.

**USER ACTION**: actually publish to HuggingFace. Codex prepares the local artifacts only.

**Acceptance:** both cards exist, lint as valid YAML+markdown.

---

## Group F — Frontend onboarding + polish (~2 hours)

### F1 — First-run onboarding overlay
**Why:** judges land on `/` cold. They need a 30-second guided tour.

**Files:** create `frontend/src/components/OnboardingTour.tsx`, modify `frontend/src/routes/Home.tsx`.

**Spec:**
- Show on first visit (localStorage flag `circuitsage:onboarded`).
- 4 steps: (1) "Try the op-amp demo", (2) "Snap a schematic photo", (3) "Pair your phone", (4) "Generate a lab report". Each step highlights the relevant UI element with a soft glow (use existing motion stack, no new deps).
- "Skip tour" button always visible.

**Acceptance:** clear localStorage in browser, reload `/` → tour shows. Dismiss → does not show again. Build still passes.

### F2 — Theme toggle (dark default → light optional)
**Files:** `frontend/src/styles.css`, `frontend/src/hooks/useA11yPrefs.tsx`, `frontend/src/components/ThemeToggle.tsx`.

**Spec:** light variant of the existing dark palette, swappable via CSS variables. Toggle in the top-right. Persist to localStorage. Honor `prefers-color-scheme`.

**Acceptance:** toggle flips the entire UI; no contrast regressions in either theme.

### F3 — Animated B-roll fallback for the demo
**Why:** S1 demo script needs a safety net if user can't film.

**Files:** create `frontend/src/routes/PressKit.tsx`, route `/press`.

**Spec:** auto-playing animated SVG/CSS sequence that walks through the demo (no audio, no real video). Uses the existing motion stack. Loops at 22 seconds. Each slide is one of the 8 demo beats from S1.

**Acceptance:** `/press` plays the loop in any modern browser; the build is still under 500 KB gzipped.

### F4 — Watch backend `gemma_status` over the chat panel
**Files:** `frontend/src/components/ChatPanel.tsx`, `frontend/src/components/GemmaStatusBanner.tsx`.

**Spec:** the chat panel shows a live chip near the input: green `agentic`, yellow `single_shot`, blue `deterministic`, red `safety_refusal`. The chip animates a soft pulse when a diagnosis is in flight.

**Acceptance:** running a diagnosis with Ollama down vs up flips the chip color visibly.

---

## Final sign-off (run once after Group F)

```bash
make test
backend/.venv/bin/python train/dataset/validate.py
bash scripts/demo_smoke.sh                           # after make demo-seed
PYTHONPATH=backend backend/.venv/bin/python train/eval/harness.py --model gemma3:4b 2>/dev/null || true
curl -s localhost:8000/api/routes | jq 'length'
git log --oneline | head -40
```

Update `docs/SUBMISSION_CHECKLIST.md` "Last verified at HEAD" line and tick every item that now passes.

If any item in Groups A–F was skipped, log the reason in `docs/BLOCKERS.md` and continue. Do not invent.

---

## Appendix — file map of new artifacts (target end state)

```
.github/workflows/ci.yml                              # A3
backend/requirements.txt                              # A1
backend/app/services/demo_seeds.py                    # A2
backend/app/services/agent_orchestrator.py            # B3
backend/app/tools/datasheet.py                        # B3
backend/app/knowledge/textbook/*.md                   # B1 (+7)
backend/app/knowledge/datasheets/*.md                 # B2 (+15)
backend/tests/integration/test_demo_flows.py          # C2
backend/tests/test_topology_pack.py                   # A5 (extend)
backend/tests/test_uncertainty_gallery.py             # D1
backend/app/main.py                                   # A7, E4
sample_data/uncertainty/<8 dirs>/*                    # D1
train/eval/{harness.py, eval_set.jsonl, README.md}    # C1
train/eval/last_run.json                              # C1 (after run)
train/dataset/card.md                                 # E5
train/output/MODEL_CARD.md                            # E5
scripts/{i18n_check.py, demo_seed.py, demo_smoke.sh, screenshots.md}  # A4, C3, C4, E3
docs/{SUBMISSION_CHECKLIST.md, DEMO_SCRIPT.md, KAGGLE_WRITEUP_DRAFT.md}  # A6, E1, E2
frontend/src/i18n/{en,hi,es,pt}.ts                    # A4 (expand)
frontend/src/components/{OnboardingTour, ThemeToggle}.tsx  # F1, F2
frontend/src/routes/PressKit.tsx                      # F3
frontend/src/components/{ChatPanel,GemmaStatusBanner}.tsx  # F4
README.md                                             # E3
Makefile                                              # C3
```

End of plan.
