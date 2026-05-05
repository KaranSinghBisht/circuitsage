# Phase 3.5 Patch — Pre-Phase-4 cleanup

**Audience:** the same Codex agent that ran `WINNING_BUILD_PLAN.md` Phases 0–3.
**Read order:** this doc *first*, before resuming with `WINNING_FORWARD_PLAN.md`.
**Time budget:** 1.5–3 hours.
**Reason:** the audit of the previous run found one fake (the LoRA dataset is 94 unique prompts duplicated 55×), two real misses (electron pin, react-native pin), and four shortcuts vs. the plan that materially weaken the submission. This doc closes them.

Operating rules carry over from `WINNING_BUILD_PLAN.md` Section 0:
- Phase-by-phase. Do not skip.
- Each item has an `Acceptance` block. Do not move on until it passes.
- Commit after each item: `git add -A && git commit -m "circuitsage: patch.<n> <summary>"`.
- Log obstacles to `docs/BLOCKERS.md`.
- Do not break the existing op-amp demo at any checkpoint.

There are 7 items. Items 1–3 are blockers. Items 4–7 close credibility gaps the writeup will be judged on.

---

## P1 — Rebuild the LoRA dataset with real diversity

### Why
`train/dataset/circuitsage_qa.jsonl` has **5,200 rows but only 94 unique user prompts** (duplication ratio 55×). `train/dataset/build.py` cycles through `(topology × fault × 5 symptoms × 5 measurements)` and emits the cartesian product. There is no real paraphrase augmentation despite an `augment.py` file. Fine-tuning on this will memorize 94 prompts, not learn circuit reasoning. The Unsloth Prize lane explicitly evaluates the *quality* of the fine-tune.

### Files
- modify `train/dataset/build.py`
- modify `train/dataset/augment.py`
- modify `train/dataset/validate.py`
- create `train/dataset/templates.py`
- (re)generate `train/dataset/circuitsage_qa.jsonl`
- modify `train/dataset/README.md`

### Spec

#### P1.1 — Per-fault template library
Create `train/dataset/templates.py` with **30–40 prompt templates per topology** that vary along these axes:

- Symptom phrasing (≥10 distinct natural phrasings per topology).
- Numeric fillers: rail voltages (±5 / ±9 / ±12 / ±15 V), input amplitudes (10 mV / 100 mV / 1 V / 5 V peak), frequencies (10 Hz / 1 kHz / 10 kHz / 100 kHz), resistor values (1 kΩ / 4.7 kΩ / 10 kΩ / 47 kΩ / 100 kΩ), capacitor values (1 nF / 10 nF / 100 nF / 1 µF / 10 µF).
- Student persona: "first-year EEE", "polytechnic", "self-taught maker", "MSc lab tutor".
- Question style: "what should I check next?", "is X the cause?", "I tried Y, now what?", "explain why my circuit does Z", "compare expected to observed".
- Negative examples: 10% of templates lead to *no* clear fault — assistant returns `confidence: low` and asks for more evidence rather than picking a fault.

Schema:
```python
@dataclass
class Template:
    topology: str
    fault_id: str | None         # None → "ask for more evidence" branch
    persona: str
    template: str                 # uses {rail}, {f}, {amp}, {rin}, {rf}, {observed} placeholders
    expected_label: str | None    # measurement label the assistant should ask for
```

`templates.py` exposes `TEMPLATES: list[Template]` and a deterministic `render(template, seed) -> tuple[str, dict]` function that fills placeholders from a `random.Random(seed)`.

#### P1.2 — Real Gemma paraphrase augmentation
Rewrite `train/dataset/augment.py` to call **Ollama Gemma** (`gemma3:4b`) and ask for `n` natural paraphrases of each rendered prompt:

```
You are paraphrasing a student's circuit-debugging question.
Rewrite the question N different ways.
Keep the technical content identical: same topology, same numeric values, same symptom.
Vary tone, length, and word order.
Return JSON: {"paraphrases": ["...", "..."]}.

Original: <text>
N: <n>
```

If Ollama is unreachable, fall back to a rule-based paraphraser (synonym swaps, sentence reordering, contraction expansion) that produces ≤2 variants per seed and **mark the row** `{"meta": {"paraphrase_source": "rule"}}`. The notebook should warn in `train/README.md` that rule-based examples should be filtered out before training if Ollama wasn't available.

#### P1.3 — Build pipeline
`build.py` orchestrates:
1. Render every template once with seed `i` for `i in range(N)` where `N` is chosen so total rendered ≥ 800 unique prompts.
2. For each rendered prompt, call `augment.paraphrase(prompt, n=4)` → 5 variants per seed (1 original + 4 paraphrases).
3. Pair each variant with the catalog-driven structured assistant answer (already in current `build.py`, keep that logic — but compute the assistant answer per the *rendered* numeric fillers, not the global symptom string).
4. Inject a 5% safety branch as before.
5. Shuffle, write JSONL.

Target shape:
- ≥1500 unique user prompts.
- 5000–8000 total rows.
- Each topology represented in 12–25% of rows (no single topology > 30%).
- Negative-evidence branch: 5–8% of rows.
- Safety branch: 4–6% of rows.

#### P1.4 — Real validator
Rewrite `train/dataset/validate.py` to assert:
- Every line is valid JSON with the chat-template shape.
- `unique_user_prompts ≥ 1500`.
- Per-topology distribution within `[0.10, 0.30]`.
- Safety rows in `[0.04, 0.06]`.
- Negative-evidence rows in `[0.04, 0.10]`.
- No row's user content appears verbatim more than 8 times.

Print a breakdown table and exit non-zero if any check fails.

### Acceptance
- `backend/.venv/bin/python train/dataset/validate.py` exits 0 and prints a topology-distribution table.
- `wc -l train/dataset/circuitsage_qa.jsonl` is in `[5000, 8000]`.
- `python -c "import json; lines=open('train/dataset/circuitsage_qa.jsonl').read().splitlines(); print(len({json.loads(L)['messages'][1]['content'] for L in lines}))"` prints `≥ 1500`.

### Pitfalls
- If Ollama `gemma3:4b` is not loaded in the run env, P1.2's fallback emits rule-based paraphrases and the run will still succeed — but the notebook README must call this out, and the validator must report the `paraphrase_source` mix so a human knows whether to re-run with Ollama up.

---

## P2 — Fix the electron pin

### Why
`apps/desktop/package.json:14` still pins `"electron": "^41.5.0"`. Electron 41 does not exist. The previous run's "verification" was `node --check main.js` (a syntax-only check that doesn't require electron installed), which is not the spec's intent. A judge running `npm install` in `apps/desktop` will fail with `ETARGET`.

### Files
- modify `apps/desktop/package.json`
- modify `apps/desktop/README.md` (create if missing)

### Spec
- Run `npm view electron version` (latest stable) at the start of the task and pin to that exact major (e.g. `^33.0.0` or whatever `latest` reports).
- Run a real `npm install` inside `apps/desktop`. If `electron-builder@^26` complains about peer-deps, lift it to a published compatible version.
- Run `npm --prefix apps/desktop start` and confirm the window opens (it will fail to reach the backend, that's fine — we only need launch to succeed).
- Update `apps/desktop/README.md` with the actual pinned version and the command order.

### Acceptance
- `npm --prefix apps/desktop install` exits 0 with no `ETARGET` errors.
- `npm --prefix apps/desktop run check` still exits 0.
- `npm view electron@<pinned-version>` returns valid metadata.

---

## P3 — Verify (and fix) the react-native pin

### Why
`apps/ios/package.json:21` pins `"react-native": "0.83.6"`. The previous run added a comment in `package.json` claiming it's published; that comment is not evidence. If RN 0.83.6 doesn't exist on npm, the iOS app cannot install.

### Files
- modify `apps/ios/package.json`
- modify root `package.json` overrides
- modify `apps/ios/README.md`

### Spec
1. Run `npm view react-native@0.83.6 version 2>&1`.
   - **If it prints a version**, the pin is valid. Remove the self-justifying comment from `package.json` (move that note to `apps/ios/README.md`). No further action.
   - **If it returns `npm error code E404`**, the pin is broken. Find the highest published `react-native` version that the installed Expo SDK supports (run `npx expo install --check` and read the recommendation, or `npm view expo@<installed> peerDependencies`). Pin both `apps/ios/package.json` and the root `overrides` to that version.
2. Run `npx expo install --check` and address every recommendation it prints.
3. Run `npm --prefix apps/ios install` end-to-end (no `--legacy-peer-deps`).

### Acceptance
- `npm --prefix apps/ios install` exits 0.
- `npx expo install --check` reports no fixable issues.
- `npm --prefix apps/ios run check` exits 0.

---

## P4 — Close the iterative agent loop (or re-label it honestly)

### Why
`backend/app/services/agent_orchestrator.py` defines tool schemas and passes `tools=` to Ollama, but the loop is single-shot: model tool calls are recorded as `_stub_tool_output` entries and **never fed back to the model**. The `gemma_status: ollama_gemma` label implies an agentic loop that does not exist. The plan's Phase 1.3 and 5.2 both required iteration. The writeup will claim "function-calling agentic loop"; right now that's not true.

### Files
- modify `backend/app/services/agent_orchestrator.py`
- modify `backend/app/services/tool_runner.py` (create)
- modify `backend/app/services/prompt_templates.py`
- create `backend/tests/test_agent_loop.py`

### Spec

#### P4.1 — Real tool execution
Move tool dispatch out of `agent_orchestrator` into a new `tool_runner.py` with one public function:

```python
async def run_tool(name: str, arguments: dict, *, context: AgentContext) -> dict
```

`AgentContext` carries: session, artifacts, measurements, netlist, waveform, comparison, fallback, settings.
Each tool name maps to a real handler:

- `compute_expected_value` → returns `expected_behavior` from `fault_catalog._expected_behavior(...)` plus catalog-derived numeric fields for the requested quantity.
- `request_measurement` → marks the named label as the agent's recommendation; returns `{"requested": label, "already_taken": <bool>}`.
- `request_image` → returns `{"requested_target": target, "available": <list of artifact ids matching kind>}`.
- `cite_textbook` → calls `rag.retrieve(topic, topology=current_topology, k=3)` and returns the top snippets.
- `verify_with_simulation` → returns the catalog's `verification_test` for the top fault plus a one-sentence simulation suggestion.

#### P4.2 — Iterative loop
Replace the current single-shot block with:

```python
async def _agentic_loop(client, system_prompt, user_prompt, history, tool_schemas, context, max_iterations=4):
    transcript = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": user_prompt}]
    recorded_calls: list[dict[str, Any]] = []
    for _ in range(max_iterations):
        chat = await client.chat(transcript, tools=tool_schemas, format_json=False)
        tool_calls = chat.get("tool_calls", [])
        if not tool_calls:
            return {"content": chat["content"], "tool_calls": recorded_calls, "iterations": _ + 1}
        transcript.append({"role": "assistant", "content": chat["content"], "tool_calls": tool_calls})
        for raw in tool_calls[:3]:
            name = raw.get("function", {}).get("name") or raw.get("name") or "unknown"
            args = raw.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                try: args = json.loads(args)
                except json.JSONDecodeError: args = {"raw": args}
            output = await run_tool(name, args, context=context)
            transcript.append({"role": "tool", "name": name, "content": json.dumps(output)})
            recorded_calls.append({"tool_name": name, "input": args, "output": output, "status": "ok"})
    # last call to coerce JSON
    transcript.append({"role": "user", "content": "Return only the structured diagnosis JSON now."})
    final = await client.chat(transcript, format_json=True)
    return {"content": final["content"], "tool_calls": recorded_calls, "iterations": max_iterations}
```

Cap iterations at 4. After the loop, `parse_json_response` the final content; if parse fails, use the catalog fallback and tag `gemma_status: ollama_partial`.

#### P4.3 — Honest status labels
Update `gemma_status` enum:
- `ollama_gemma_agentic` — loop ran, ≥1 tool call executed, final JSON parsed.
- `ollama_gemma_single_shot` — loop produced a final JSON without tool calls.
- `ollama_partial` — loop ran but final JSON failed to parse; catalog fallback used.
- `deterministic_fallback` — Ollama unreachable or errored.
- `blocked_by_safety` — unchanged.

The `confidence` chip in the UI maps these accordingly.

### Acceptance
- New test `backend/tests/test_agent_loop.py` mocks Ollama, returns a tool call on iteration 1 and a final JSON on iteration 2; asserts `iterations == 2`, `tool_calls` has the executed call with a real `output` (not `stub: True`), and `gemma_status == "ollama_gemma_agentic"`.
- Existing tests still pass.
- A live test (Ollama up): a typical op-amp diagnosis records ≥1 tool call with a non-stub output.

---

## P5 — Real embeddings + real vector store

### Why
`backend/app/services/embedder.py` is normalized token counts (bag-of-words TF cosine) and `backend/app/services/vectorstore.py` rewrites a single JSON file on every ingest. The plan called for Ollama `nomic-embed-text` embeddings (with sentence-transformers fallback) and Chroma persistent / sqlite-vss. RAG quality matters for both demo questions and the Kaggle writeup's claim of "real RAG over a curated corpus".

### Files
- rewrite `backend/app/services/embedder.py`
- rewrite `backend/app/services/vectorstore.py`
- modify `backend/requirements.txt`
- modify `scripts/ingest_corpus.py`
- modify `backend/tests/test_vectorstore.py`
- modify `backend/tests/test_rag.py`

### Spec

#### P5.1 — Embedder
- Primary path: call `POST {OLLAMA_BASE_URL}/api/embeddings` with `{"model": OLLAMA_EMBED_MODEL, "prompt": text}` and return the `embedding` vector. Default model `nomic-embed-text` (384-d). Document the `ollama pull nomic-embed-text` step in `scripts/install.sh`.
- Fallback: `sentence-transformers` `all-MiniLM-L6-v2` (also 384-d). Lazy import — only if the Ollama call fails. Add `sentence-transformers==3.3.1` to `requirements.txt`.
- Last-resort fallback: keep the bag-of-words function as `bow_embed_text` and use it only when both above fail; tag the record `metadata.embedder = "bow"`.
- Public API: `embed_text(text: str) -> list[float]` (dense). Update vectorstore signatures accordingly.

#### P5.2 — Vector store
Use **Chroma persistent client** with the DuckDB+Parquet backend. Persist to `backend/app/data/chroma/`.

```python
import chromadb
from chromadb.config import Settings as ChromaSettings

_client = chromadb.PersistentClient(path=str(get_settings().database_path.parent / "chroma"))
_collection = _client.get_or_create_collection("circuitsage")

def ingest(doc_id, text, metadata):
    _collection.upsert(ids=[doc_id], embeddings=[embed_text(text)], documents=[text], metadatas=[metadata or {}])

def query(text, k=5, filter=None):
    res = _collection.query(query_embeddings=[embed_text(text)], n_results=k, where=filter or None)
    return [{"doc_id": id, "source": meta.get("source", id), "text": doc, "metadata": meta, "score": float(1 - dist)}
            for id, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]
```

Add `chromadb>=0.5.20` to `requirements.txt`. If Chroma's wheels don't install on the run machine, fall back to `sqlite-vss` and document in BLOCKERS.md.

#### P5.3 — Re-ingest
After the rewrite, run `python scripts/ingest_corpus.py` once to repopulate the store. The old JSON store at `backend/app/data/vectorstore.json` should be deleted (`scripts/ingest_corpus.py` removes it).

### Acceptance
- `backend/.venv/bin/python -c "from backend.app.services.vectorstore import query; print([h['source'] for h in query('non-inverting input floating')])"` returns `faults/floating_noninv_input.md` as the top hit.
- Backend tests still pass; new tests assert dense vector dimensionality (`>= 256`) and that filter-by-topology works.
- The op-amp seed `tool_calls` includes a `retrieve` entry whose top snippet comes from `faults/floating_noninv_input.md` (existing behavior preserved).

---

## P6 — Tighten chat-memory regex

### Why
`agent_orchestrator._measurements_from_messages` extracts numbers with bare patterns like `\b(gain|vout/vin)\b[^0-9+-]*([+-]?\d+(?:\.\d+)?)`. Sentences such as *"the expected gain is 4.7"* will be silently captured as a measured fact and used to bias fault scoring. That's a hallucination risk under judging.

### Files
- modify `backend/app/services/agent_orchestrator.py`
- modify `backend/tests/test_chat_memory.py`

### Spec
- Require an explicit measurement-context phrase before the value. New patterns:
  ```
  (i\s+(?:measured|got|read|saw|see)|measured(?:\s+a)?|reading\s+(?:was|is|of)|the\s+meter\s+(?:shows|read|reads)|i\s+have\s+about|comes\s+out\s+to|came\s+out\s+to)
  ```
  Then a small window (≤20 chars) before the value capture.
- Bind to label tokens that are clearly observational, not theoretical: keep `V_noninv`, `V+`, `V-`, `Vc`, `loaded_vout`, `Vout`. Drop the bare `gain`/`vout/vin` patterns from the chat-memory extractor entirely — let the user upload a measurement explicitly for those.
- Add a `min_uncertainty_token` flag: if the same message includes phrases like "expected", "should be", "predicted", "in theory", "the lab manual says", skip extraction.
- Tag every extracted measurement `metadata.source = "chat_memory_inferred"` and `metadata.confidence = "low"` so the UI can show it differently.

### Acceptance
- New test: input `"My circuit's expected gain is 4.7."` produces 0 extracted measurements.
- New test: input `"I measured V_noninv at the bench and got 2.8 V."` produces 1 extracted measurement with `value == 2.8` and `metadata.source == "chat_memory_inferred"`.
- New test: input `"The lab manual says the rail should be 12 V."` produces 0 extracted measurements.

---

## P7 — Verify Phase 0.5 frontend banner and Phase 0.7 README

### Why
Codex's Phase-3 summary claimed both. The audit didn't directly inspect them. Submission day reviewers will see them first.

### Files
- inspect `frontend/src/main.tsx` (and any new `frontend/src/components/GemmaStatusBanner.tsx`)
- inspect `README.md`

### Spec
- Confirm a `GemmaStatusBanner` component (or equivalent) exists, polls `/api/health/model` every 10 s, and renders an amber banner when `loaded === false` or `available === false`.
- Confirm the diagnosis card chip color-codes by `gemma_status`. Add the new statuses from P4 (`ollama_gemma_agentic`, `ollama_gemma_single_shot`, `ollama_partial`).
- Confirm the README opens with the tagline, the Quickstart is `make install && make demo`, and there are no dead links.

If anything is missing, implement it. Keep the file under 800 lines.

### Acceptance
- Stop Ollama → reload Studio → amber banner appears.
- Start Ollama with `gemma3:4b` → reload Studio → banner disappears.
- Diagnosis card chip changes color when the status changes.
- `npm --prefix frontend run build` exits 0.

---

## Phase 3.5 sign-off

When all 7 items pass:

```bash
make test
backend/.venv/bin/python train/dataset/validate.py
bash scripts/check_ollama.sh
curl -s -X POST localhost:8000/api/sessions/seed/op-amp | jq '.seed_diagnosis | {gemma_status, top_id: .likely_faults[0].id, tool_calls: (.tool_calls | length)}'
git log --oneline -10
```

Expected:
- `make test` exits 0.
- Validator prints a healthy distribution table.
- Op-amp seed returns `gemma_status: ollama_gemma_agentic` (Ollama up) or `deterministic_fallback` (Ollama down), and `tool_calls.length >= 4`.
- Git log shows 7 patch commits with `circuitsage: patch.<n>` messages.

After sign-off, proceed to `docs/WINNING_FORWARD_PLAN.md`.
