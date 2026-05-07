# CircuitSage Cleanup + Kaggle Eval Implementation Plan

**Goal:** Get CircuitSage submission-ready by 2026-05-18 with stale docs fixed, real eval metrics from a Kaggle GPU kernel (no local Ollama), HuggingFace upload templates, and a v1.0.0-submission release notes draft.

**Architecture:** Three sequential workstreams — (1) doc + state hygiene cleanup, (2) new `train/kaggle_eval/` kernel that runs the existing eval harness against `gemma-3-4b-it` on Kaggle T4 and writes the same metrics dict our local harness would, (3) HuggingFace upload scripts + release notes + writeup linkage.

**Tech Stack:** Markdown docs, Python eval harness, Kaggle CLI (already authenticated), HuggingFace Hub Python client, Jupyter notebooks.

## Constraints

- No local Ollama (user's Mac runs out of RAM).
- Kaggle CLI is authenticated; user has previously pushed `circuitsage-faults-v1`, `circuitsage-gemma-lora`, `circuitsage-writeup`.
- HuggingFace token NOT available locally — HF scripts ship as user-runnable templates.
- 75 commits unpushed on `master`; GitHub push blocked on `gh auth refresh -h github.com -s workflow`.
- Hackathon deadline: 2026-05-18 (T-11 days).

## File Map

**New:**
- `train/kaggle_eval/kernel-metadata.json`
- `train/kaggle_eval/circuitsage_eval.ipynb`
- `train/kaggle_eval/README.md`
- `train/dataset/DATASET_CARD.md`
- `scripts/hf_upload_dataset.py`
- `scripts/hf_upload_model.py`
- `docs/RELEASE_NOTES_v1.0.0.md`

**Modified:**
- `train/README.md` (5,200 → 6,000)
- `docs/PHASE_3_5_PATCH.md` (annotate historical 5,200)
- `.gitignore` (add `.omc/state/` churn)
- `docs/BLOCKERS.md` (2026-05-07 entries)
- `docs/KAGGLE_WRITEUP_DRAFT.md` (link to eval kernel; replace TBD with kernel-derived numbers once available)

---

## Tasks

### Task 1: Fix `train/README.md` row count

**Files:**
- Modify: `train/README.md`

- [ ] Read `train/README.md`
- [ ] Edit line 12: replace `5,200 validated chat examples` with `6,000 validated chat examples (4,978 unique prompts after deduplication)`
- [ ] Verify: `grep -n "5,200\|5200\|6,000" train/README.md` — expect only `6,000` and `4,978` matches
- [ ] Stage: `git add train/README.md`

### Task 2: Annotate historical row count in `PHASE_3_5_PATCH.md`

**Files:**
- Modify: `docs/PHASE_3_5_PATCH.md`

- [ ] Read line 22 (the "5,200 rows but only 94 unique user prompts" line)
- [ ] Append a one-line note prefixed `> Resolved 2026-05-07:` explaining dataset was rebuilt to 6,000 rows / 4,978 unique prompts via paraphrase augmentation
- [ ] Stage: `git add docs/PHASE_3_5_PATCH.md`

### Task 3: Add `.gitignore` entries for `.omc/state` churn

**Files:**
- Modify: `.gitignore`

- [ ] Read `.gitignore`
- [ ] Append:
  ```
  # OMC orchestration state (per-session churn)
  .omc/state/agent-replay-*.jsonl
  .omc/state/idle-notif-cooldown.json
  .omc/state/last-tool-error.json
  .omc/state/mission-state.json
  .omc/state/subagent-tracking.json
  .omc/state/checkpoints/
  .omc/project-memory.json
  ```
- [ ] Run: `git rm --cached .omc/state/agent-replay-*.jsonl .omc/state/idle-notif-cooldown.json .omc/state/mission-state.json .omc/state/subagent-tracking.json .omc/project-memory.json 2>/dev/null || true`
- [ ] Verify: `git status --short` shows only intended changes
- [ ] Stage: `git add .gitignore`

### Task 4: Refresh `docs/BLOCKERS.md` with 2026-05-07 entries

**Files:**
- Modify: `docs/BLOCKERS.md`

- [ ] Read tail of `docs/BLOCKERS.md`
- [ ] Append three new sections under `## Submission week (2026-05-07)`:
  - `Local Ollama unavailable` — user's Mac OOMs running gemma3:4b + gemma4:e4b. Eval moved to Kaggle GPU kernel (`train/kaggle_eval/`).
  - `GitHub push pending workflow scope` — 75 unpushed commits; user must run `gh auth refresh -h github.com -s workflow` before `git push -u origin master`.
  - `HuggingFace publication` — dataset and model cards ready; user runs `scripts/hf_upload_dataset.py` and `scripts/hf_upload_model.py` with their HF token.
- [ ] Stage: `git add docs/BLOCKERS.md`

### Task 5: Create Kaggle eval kernel

**Files:**
- Create: `train/kaggle_eval/kernel-metadata.json`
- Create: `train/kaggle_eval/circuitsage_eval.ipynb`
- Create: `train/kaggle_eval/README.md`

#### Sub-step 5a: kernel metadata
- [ ] Write `train/kaggle_eval/kernel-metadata.json`:
  ```json
  {
    "id": "karansinghbisht/circuitsage-eval",
    "id_no": null,
    "title": "circuitsage-eval",
    "code_file": "circuitsage_eval.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": "false",
    "enable_gpu": "true",
    "enable_tpu": "false",
    "enable_internet": "true",
    "dataset_sources": ["karansinghbisht/circuitsage-faults-v1"],
    "competition_sources": [],
    "kernel_sources": []
  }
  ```

#### Sub-step 5b: notebook
- [ ] Write `train/kaggle_eval/circuitsage_eval.ipynb` — a Jupyter notebook with:
  1. Markdown intro: purpose, dataset link, model used.
  2. Pip install: `transformers==4.46.3 accelerate==1.1.1 bitsandbytes==0.43.3 huggingface_hub==0.26.2`.
  3. Imports + huggingface_hub login from `KAGGLE_USERNAME` / `KAGGLE_KEY` secrets (the model gating; user needs HF token in Kaggle Secrets as `HF_TOKEN`).
  4. Load `google/gemma-3-4b-it` with 4-bit BitsAndBytesConfig.
  5. Load eval set from `/kaggle/input/circuitsage-faults-v1/eval_set.jsonl` (200 rows).
  6. Iterate, build prompt from system+user messages, generate JSON, parse, score.
  7. Compute: `schema_validity_rate`, `experiment_type_exact_match`, `top_fault_id_match`, `safety_refusal_precision`, `safety_refusal_recall`, `mean_latency_ms`.
  8. Print summary table and write `/kaggle/working/last_run.json` for download.

#### Sub-step 5c: README
- [ ] Write `train/kaggle_eval/README.md` documenting:
  - How to push: `kaggle kernels push -p train/kaggle_eval`
  - Required Kaggle Secrets: `HF_TOKEN` (gemma-3 is HF-gated)
  - Expected runtime: ~10-15 minutes on T4
  - How to retrieve `last_run.json` for the writeup

#### Sub-step 5d: validate notebook structure
- [ ] Run: `python -c "import json; nb=json.load(open('train/kaggle_eval/circuitsage_eval.ipynb')); assert nb['nbformat'] == 4; assert len(nb['cells']) >= 6; print('cells:', len(nb['cells']))"` — expect `cells: >=6` no error
- [ ] Run: `python -c "import json; json.load(open('train/kaggle_eval/kernel-metadata.json'))"` — expect no error
- [ ] Stage: `git add train/kaggle_eval/`

### Task 6: Create `train/dataset/DATASET_CARD.md`

**Files:**
- Create: `train/dataset/DATASET_CARD.md`

- [ ] Write a HuggingFace-style dataset card with: YAML frontmatter (license MIT, language en, tags `circuit-analysis,fault-diagnosis,gemma`), Description, Dataset structure (6,000 rows with `messages` list), Source code (`train/dataset/build.py` cycles topology × fault × symptoms × measurements), Splits (none — full set), Considerations (synthetic; deduplication ratio).
- [ ] Stage: `git add train/dataset/DATASET_CARD.md`

### Task 7: Create HF upload templates

**Files:**
- Create: `scripts/hf_upload_dataset.py`
- Create: `scripts/hf_upload_model.py`

#### Sub-step 7a: dataset upload
- [ ] Write `scripts/hf_upload_dataset.py`:
  - `from huggingface_hub import HfApi, login`
  - reads `HF_TOKEN` env var, errors clearly if missing
  - creates repo `karansinghbisht/circuitsage-faults` (type=dataset)
  - uploads `train/dataset/circuitsage_qa.jsonl`, `train/eval/eval_set.jsonl`, `train/dataset/DATASET_CARD.md`

#### Sub-step 7b: model upload
- [ ] Write `scripts/hf_upload_model.py`:
  - same login pattern
  - creates repo `karansinghbisht/circuitsage-lora` (type=model)
  - uploads `train/output/MODEL_CARD.md` and (when present) `train/output/circuitsage-lora-q4_k_m.gguf`
  - prints next step: `ollama create circuitsage:latest`

#### Sub-step 7c: validate
- [ ] Run: `python -c "import ast; ast.parse(open('scripts/hf_upload_dataset.py').read()); ast.parse(open('scripts/hf_upload_model.py').read()); print('ok')"` — expect `ok`
- [ ] Stage: `git add scripts/hf_upload_dataset.py scripts/hf_upload_model.py`

### Task 8: Create `docs/RELEASE_NOTES_v1.0.0.md`

**Files:**
- Create: `docs/RELEASE_NOTES_v1.0.0.md`

- [ ] Write release notes with sections:
  - Headline (one-line: "CircuitSage v1.0.0 — offline-first AI lab partner for analog circuits")
  - What's new (multimodal Gemma agent, 13 topology seeds, 39 fault dictionary, educator dashboard, iOS LAN companion, hosted/self-host parity, 6,000-row LoRA dataset)
  - How to run (3 commands: `make install`, `ollama pull gemma3:4b`, `make run`)
  - Demo (Kaggle writeup link, Kaggle dataset link, Kaggle eval kernel link, GitHub repo link)
  - Known limits (USER ACTION items: Kaggle training kernel via Unsloth template, iOS device test, Fly deploy, demo video)
  - License: MIT
- [ ] Stage: `git add docs/RELEASE_NOTES_v1.0.0.md`

### Task 9: Link eval kernel from `KAGGLE_WRITEUP_DRAFT.md`

**Files:**
- Modify: `docs/KAGGLE_WRITEUP_DRAFT.md`

- [ ] Read lines 49-55 (eval section)
- [ ] Replace lines 51 + 53 with text that points to `https://www.kaggle.com/code/karansinghbisht/circuitsage-eval` as the source of truth for live metrics, while keeping the metric-name list intact
- [ ] Add a new sentence: "Once the eval kernel finishes, pull `last_run.json` and replace the placeholders below with the captured numbers."
- [ ] Stage: `git add docs/KAGGLE_WRITEUP_DRAFT.md`

### Task 10: Final commit

**Files:** none new

- [ ] Run: `git status --short` — verify staged set is exactly the expected files
- [ ] Commit:
  ```
  git commit -m "$(cat <<'EOF'
  circuitsage: submission-week cleanup + kaggle eval kernel + hf templates
  
  - fix train/README row count (5,200 -> 6,000)
  - annotate historical row count in PHASE_3_5_PATCH
  - gitignore .omc/state per-session churn
  - refresh BLOCKERS with 2026-05-07 entries
  - add train/kaggle_eval kernel + README
  - add train/dataset/DATASET_CARD.md
  - add scripts/hf_upload_{dataset,model}.py templates
  - add docs/RELEASE_NOTES_v1.0.0.md
  - link eval kernel from KAGGLE_WRITEUP_DRAFT
  
  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  EOF
  )"
  ```
- [ ] Run: `git status` — expect clean working tree
- [ ] Output one line to user: "All set. Run `gh auth refresh -h github.com -s workflow` then `git push -u origin master` to publish."

---

## Out-of-scope (USER ACTION, documented in BLOCKERS)

- Pushing the Kaggle eval kernel (user runs `kaggle kernels push -p train/kaggle_eval`).
- Setting Kaggle Secret `HF_TOKEN` for gemma-3 gating.
- Flipping `circuitsage-faults-v1` Kaggle dataset to public.
- Running HF upload scripts (needs HF token).
- Re-running the LoRA training kernel via Unsloth template.
- iOS physical device validation.
- Fly.io deploy.
- Demo video shoot.
- `gh auth refresh -h github.com -s workflow` + `git push`.
- Tagging `v1.0.0-submission` (after the push lands).

## Definition of Done

- `make test` still green (103 backend tests).
- `git status` clean after Task 10.
- New eval kernel pushable to Kaggle (validated as parseable JSON + Jupyter notebook locally).
- `docs/RELEASE_NOTES_v1.0.0.md` exists with all required sections.
- `docs/BLOCKERS.md` has 2026-05-07 section with clear next-step actions for the user.
