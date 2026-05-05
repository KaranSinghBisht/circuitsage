# CircuitSage Agent Handoff

**Project:** CircuitSage  
**Tagline:** Stack traces for circuits.  
**Subtitle:** An offline Gemma-powered lab partner for electronics students.  
**Hackathon:** Gemma 4 Good Hackathon  
**Primary track:** Future of Education  
**Secondary tracks:** Digital Equity & Inclusivity, Safety & Trust  
**Special technology target:** Ollama first; Cactus/LiteRT as stretch; Unsloth only if time remains.

---

## 0. Give this whole document to Claude Code / Codex first

Use this as the project brief. The coding agent should treat this document as the source of truth unless the human overrides it.

### One-shot build instruction for Claude Code / Codex

```text
You are building CircuitSage, a local-first AI lab partner for electrical/electronics students.

Goal: Create a functional proof-of-concept for the Gemma 4 Good Hackathon.

Core demo: A student starts an Op-Amp Inverting Amplifier lab on the PC, uploads simulation/lab artifacts, pairs a phone bench session through QR, captures/enters real-world oscilloscope/multimeter observations, and CircuitSage uses Gemma via Ollama + structured tools to diagnose the likely issue, ask for the next measurement, and generate a post-lab learning report.

Build a monorepo with:
- backend: FastAPI, SQLite, Pydantic models, file upload, session memory, tool functions, Ollama client, diagnosis orchestrator.
- frontend: Next.js PWA or simple React/Vite app with PC Studio and mobile Bench Mode pages.
- sample_data: op-amp lab manual excerpt, LTspice-like netlist, MATLAB/CSV waveform, placeholder oscilloscope/breadboard images.
- docs: demo script and architecture notes.

The MVP must be demoable even if the user does not have LTspice/MATLAB installed. Use parsers and deterministic fallback tools for sample netlists/CSV/images. Actual integrations can be plug-in stubs.

Do not build a generic chatbot. Build a persistent lab workflow: Pre-Lab -> Bench Mode -> Diagnosis -> Reflection.
```

---

## 1. Context from our ideation

We explored many Gemma 4 Good ideas: medical literacy, local-language education, disaster response, agriculture, accessibility, and electronics education. The final chosen direction is **CircuitSage** because it has the best combination of:

- authentic founder-problem fit for an Electrical/Electronics student,
- less competition than generic health/education/agriculture assistants,
- strong visual demo potential,
- clear use of Gemma 4 capabilities,
- real utility after the hackathon.

The core insight:

> Software students get stack traces. Electronics students get silence.

When code fails, it gives errors. When a circuit fails, students see a flat oscilloscope, wrong voltage, smoke, heat, or nothing at all. Debugging requires mentorship at the bench. In many labs, one instructor must help dozens of students, so students guess, copy lab records, or give up.

CircuitSage gives each student a patient offline lab partner that follows the circuit from simulation to real hardware.

---

## 2. Hackathon strategy

The hackathon is weighted heavily toward story and real-world impact. Technical execution matters, but it should support a powerful demo.

### What the judges need to feel

The judges should understand this in the first 20 seconds:

> Learning electronics is not like learning software. A broken circuit often gives no error message. CircuitSage turns that silence into a step-by-step debugging path.

### Scoring strategy

- **Impact & Vision:** practical electronics mentorship does not scale globally. Hardware skills are needed for energy, robotics, medical devices, EVs, climate sensors, space, infrastructure, and repair economies. But students need expensive labs and human bench mentorship. CircuitSage makes some of that mentorship portable and local-first.
- **Video Storytelling:** show a student moving from PC simulation to physical lab, failing silently, then using the phone camera + Gemma to diagnose and fix the issue.
- **Technical Depth:** use Gemma 4 locally via Ollama, multimodal inputs, function/tool calling, persistent session memory, RAG over lab manual, waveform/netlist tools, and safety checks.

### Submission artifacts to plan for

- Public GitHub repository.
- Live demo URL or local demo instructions.
- 3-minute YouTube video.
- Kaggle writeup under 1,500 words.
- Media gallery with cover image/screenshots.

---

## 3. Product definition

### Name

**CircuitSage**

### Tagline options

- **Stack traces for circuits.**
- **The AI lab partner for electronics students.**
- **From simulation to oscilloscope, one persistent lab companion.**

### One-liner

CircuitSage is a connected PC + mobile AI lab partner that understands a student’s simulation, lab manual, measurements, and bench photos, then guides them through the next debugging step.

### Product thesis

CircuitSage is not a generic tutor and not a generic chatbot. It is a workflow tool for the real EEE lab loop:

```text
Pre-lab theory -> PC simulation -> physical build -> measurements -> debugging -> lab report/viva reflection
```

### Target users

Primary:

- Electrical/Electronics undergraduates.
- Polytechnic/vocational electronics students.
- Students in crowded or under-resourced labs.

Secondary:

- Lab instructors who need help scaling feedback.
- Makerspace learners.
- Repair-training students.
- First-generation hardware learners.

---

## 4. Core UX: connected PC + mobile workflow

### 4.1 PC app: CircuitSage Studio

The PC app is the workspace brain.

It handles:

- Lab session creation.
- Lab manual upload.
- LTspice-style netlist/schematic screenshot upload.
- MATLAB plot/CSV/script upload.
- Datasheet upload.
- Simulation expectation extraction.
- Persistent memory.
- Diagnosis timeline.
- Report generation.

PC Studio UI sections:

1. **Lab Session Overview**
   - Experiment name.
   - Goal.
   - Files attached.
   - Expected behavior.
   - Current issue.
   - Next recommended measurement.

2. **Artifacts Panel**
   - Lab manual PDF/text.
   - Netlist/simulation file.
   - Waveform CSV/plot image.
   - Bench images from phone.
   - Measurements.

3. **CircuitSage Agent Panel**
   - Chat-like interface, but structured around diagnosis.
   - Shows tool calls and reasoning summary.
   - Shows confidence and next measurement.

4. **Report / Reflection Panel**
   - Lab report draft.
   - Error analysis.
   - Viva questions.
   - Personal mistake memory.

### 4.2 Mobile app: CircuitSage Bench Mode

The phone is the eyes and ears in the lab.

The student opens the phone browser, scans a QR from the PC, and joins the current lab session.

Bench Mode handles:

- Camera capture for breadboard.
- Camera capture for oscilloscope screen.
- Camera capture for multimeter reading.
- Voice/text question entry.
- Manual measurement entry.
- “Ask me what to measure next” interaction.

MVP can be a PWA served by the local FastAPI/Next server:

```text
http://<laptop-ip>:8000/bench/<session_id>
```

### 4.3 Pairing flow

1. Student opens CircuitSage Studio on PC.
2. Creates/loads lab session.
3. Clicks “Start Bench Mode.”
4. PC shows QR code.
5. Phone scans QR and opens session.
6. Phone uploads photos/measurements into the same session.
7. PC updates in real time or after refresh.

Implementation options:

- MVP: HTTP polling every 2–3 seconds.
- Better: WebSocket updates.
- Simplest: same backend, shared SQLite DB, session ID in URL.

---

## 5. MVP vertical slice

Do not support every circuit. Build one polished hero demo.

### Hero experiment

**Inverting Op-Amp Amplifier**

Why this is ideal:

- Has clean theory: `Vout = -Rf/Rin * Vin`.
- Easy expected behavior.
- Easy common mistakes.
- Easy waveform comparison.
- Good visual oscilloscope demo.
- Maps well to simulation -> bench gap.

### Demo circuit configuration

```text
Circuit: Inverting op-amp amplifier
Op-amp: generic 741/TL081-like model for demo
Rin: 10 kΩ
Rf: 47 kΩ
Expected gain: -4.7
Input: 1 V peak sine wave, 1 kHz
Supply rails: +12 V and -12 V
Expected output: inverted sine wave around 4.7 V peak, not saturated
Observed failure: output stuck/clipped near +12 V
Likely fault: non-inverting input floating / missing ground reference
```

### The key diagnosis path

CircuitSage should guide like this:

1. Confirm simulation expected gain.
2. Compare observed oscilloscope output to expected output.
3. Recognize saturation/clipping.
4. Ask for supply rail measurements.
5. Ask for non-inverting input voltage.
6. Diagnose missing/floating ground reference or feedback issue.
7. Recommend correction.
8. Generate explanation and lab report note.

### Required demo artifacts

Create these sample files in `sample_data/op_amp_lab/`:

- `lab_manual_excerpt.md`
- `opamp_inverting.cir` or `opamp_inverting.net`
- `expected_waveform.csv`
- `observed_saturated_waveform.csv`
- `student_question.txt`
- `scope_saturated_placeholder.png`
- `breadboard_placeholder.png`
- `fixed_scope_placeholder.png`

If images are not available, generate simple placeholder images using Python/matplotlib/PIL:

- Expected sine wave image.
- Saturated/clipped waveform image.
- Fixed waveform image.

---

## 6. MVP feature list

### Must-have features

1. **Create Lab Session**
   - experiment name, student level, notes.

2. **Upload Artifacts**
   - PDF/text/manual file.
   - netlist file.
   - CSV waveform file.
   - image upload from PC or phone.

3. **Parse Circuit Context**
   - parse simple resistor values from netlist.
   - detect experiment type as op-amp inverting amplifier.
   - compute expected gain.

4. **Bench Mode Pairing**
   - QR code opens mobile session.
   - phone can upload image and measurement.

5. **Measurement Entry**
   - node label, value, unit, source.
   - examples: `Vout = +11.8 V DC`, `V+ = +12.1 V`, `V- = -12.0 V`, `V_noninv = 2.8 V floating`.

6. **Diagnosis Agent**
   - calls deterministic tools.
   - calls Gemma via Ollama for natural-language explanation.
   - returns structured result with likely faults, confidence, next measurement, safety notes.

7. **Report Generation**
   - post-lab summary.
   - what went wrong.
   - corrected concept.
   - viva questions.

8. **Safety Checks**
   - low-voltage lab circuits only.
   - if mains/high voltage is mentioned, warn and refuse detailed live debugging.

### Nice-to-have features

- Real WebSocket updates.
- Image annotation overlays.
- TTS voice output.
- Offline installation script.
- MATLAB `.m` parsing.
- Tinkercad `.ino` parsing.
- Fault Lab practice cases.
- Unsloth fine-tuned mini-model.

### Explicitly out of scope for MVP

- Full LTspice automation.
- Full MATLAB Engine integration.
- Full Tinkercad browser automation.
- Perfect breadboard component detection.
- Real OCR of arbitrary oscilloscope screens.
- High-voltage/mains diagnostics.
- All circuit types.

---

## 7. Recommended architecture

### Simple monorepo

```text
circuitsage/
  README.md
  SPEC.md
  .env.example
  docker-compose.yml                 # optional

  backend/
    pyproject.toml or requirements.txt
    app/
      main.py
      config.py
      database.py
      models.py
      schemas.py
      routers/
        sessions.py
        uploads.py
        bench.py
        diagnose.py
        reports.py
      services/
        ollama_client.py
        agent_orchestrator.py
        prompt_templates.py
        session_memory.py
        rag.py
      tools/
        parse_netlist.py
        waveform_analysis.py
        measurement_compare.py
        safety_check.py
        fault_reasoner.py
        report_builder.py
      data/
        circuitsage.db
      uploads/

  frontend/
    package.json
    src/
      main.tsx or app/
      pages or routes/
        index
        studio/[sessionId]
        bench/[sessionId]
      components/
        SessionList
        ArtifactUpload
        AgentPanel
        BenchCapture
        MeasurementForm
        DiagnosisCard
        ReportPanel
        ToolCallTimeline
      lib/
        api.ts
        types.ts

  sample_data/
    op_amp_lab/
      lab_manual_excerpt.md
      opamp_inverting.net
      expected_waveform.csv
      observed_saturated_waveform.csv
      student_question.txt
      scope_saturated_placeholder.png
      breadboard_placeholder.png
      fixed_scope_placeholder.png

  docs/
    DEMO_SCRIPT.md
    ARCHITECTURE.md
    KAGGLE_WRITEUP_DRAFT.md
```

### Backend stack

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- SQLite via SQLModel or SQLAlchemy
- python-multipart for uploads
- qrcode for QR generation
- pandas/numpy for waveform CSV analysis
- Pillow for image handling
- httpx for Ollama API calls

### Frontend stack

Choose one:

Option A, fastest:

- Vite + React + TypeScript
- Tailwind CSS
- Browser camera capture through `<input type="file" accept="image/*" capture="environment">`

Option B, more polished:

- Next.js + TypeScript + Tailwind
- PWA-ready routes

### Local model

Use Gemma 4 through Ollama for the demo.

Environment variable:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:latest
```

Because exact local model tags may vary, code should let the user configure `OLLAMA_MODEL`. Do not hardcode a single tag.

---

## 8. Database schema

Use SQLite. Models can be simple.

### Tables

#### `lab_sessions`

```json
{
  "id": "uuid",
  "title": "Inverting Op-Amp Amplifier",
  "student_level": "2nd/3rd year EEE",
  "experiment_type": "op_amp_inverting",
  "status": "pre_lab | bench | diagnosing | resolved | archived",
  "created_at": "datetime",
  "updated_at": "datetime",
  "summary": "string"
}
```

#### `artifacts`

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "kind": "manual | netlist | waveform_csv | image | matlab | tinkercad_code | note",
  "filename": "string",
  "path": "string",
  "text_excerpt": "string optional",
  "metadata_json": {}
}
```

#### `measurements`

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "label": "Vout",
  "value": 11.8,
  "unit": "V",
  "mode": "DC",
  "context": "output stuck near positive rail",
  "source": "manual_entry | image | voice",
  "created_at": "datetime"
}
```

#### `diagnoses`

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "diagnosis_json": {},
  "created_at": "datetime"
}
```

#### `messages`

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "role": "user | assistant | tool",
  "content": "string",
  "metadata_json": {},
  "created_at": "datetime"
}
```

---

## 9. API endpoints

### Sessions

```http
POST /api/sessions
GET /api/sessions
GET /api/sessions/{session_id}
PATCH /api/sessions/{session_id}
DELETE /api/sessions/{session_id}
```

### Uploads

```http
POST /api/sessions/{session_id}/artifacts
GET /api/sessions/{session_id}/artifacts
GET /api/artifacts/{artifact_id}/download
```

### Bench pairing

```http
POST /api/sessions/{session_id}/bench/start
GET /api/sessions/{session_id}/bench/qr
GET /bench/{session_id}                  # frontend route
```

### Measurements

```http
POST /api/sessions/{session_id}/measurements
GET /api/sessions/{session_id}/measurements
```

### Diagnosis

```http
POST /api/sessions/{session_id}/diagnose
GET /api/sessions/{session_id}/diagnoses
```

### Chat / agent

```http
POST /api/sessions/{session_id}/chat
```

Input:

```json
{
  "message": "My output is stuck at +12V",
  "mode": "pre_lab | bench | report"
}
```

Output:

```json
{
  "reply": "string",
  "diagnosis": {},
  "tool_calls": [],
  "next_measurement": {},
  "safety": {}
}
```

### Reports

```http
POST /api/sessions/{session_id}/report
GET /api/sessions/{session_id}/report
```

---

## 10. Core data contracts

### Diagnosis result schema

```json
{
  "experiment_type": "op_amp_inverting",
  "expected_behavior": {
    "gain": -4.7,
    "output": "inverted sine wave, about 4.7 V peak for 1 V peak input"
  },
  "observed_behavior": {
    "summary": "Output is stuck near the positive supply rail",
    "evidence": ["Vout = +11.8 V DC", "scope image suggests clipping/saturation"]
  },
  "likely_faults": [
    {
      "fault": "Floating or incorrectly biased non-inverting input",
      "confidence": 0.78,
      "why": "A floating reference input can drive the op-amp into saturation even when the feedback network is correct."
    },
    {
      "fault": "Feedback path disconnected or wired to wrong node",
      "confidence": 0.55,
      "why": "Without negative feedback, an op-amp can saturate at a rail."
    },
    {
      "fault": "Power rail or common ground issue",
      "confidence": 0.42,
      "why": "Missing common reference between source, scope, and circuit can create misleading measurements."
    }
  ],
  "next_measurement": {
    "label": "Voltage at non-inverting input pin",
    "expected": "approximately 0 V",
    "instruction": "Measure the voltage at the non-inverting input with respect to circuit ground before changing resistor values."
  },
  "safety": {
    "risk_level": "low_voltage_lab",
    "warnings": ["Do not debug live mains circuits with CircuitSage.", "Power off before rewiring the op-amp pins."]
  },
  "student_explanation": "Your gain calculation may be correct. The physical circuit is saturating because the op-amp likely does not have a stable reference or negative feedback path.",
  "confidence": "medium_high"
}
```

### Tool call object

```json
{
  "tool_name": "compare_expected_vs_observed",
  "input": {},
  "output": {},
  "status": "ok | error",
  "duration_ms": 34
}
```

---

## 11. Tooling layer

Gemma should orchestrate tools. Deterministic tools create credibility.

### Tool 1: `parse_netlist`

Input:

```json
{"path": "sample_data/op_amp_lab/opamp_inverting.net"}
```

Output:

```json
{
  "components": [
    {"ref": "Rin", "value_ohms": 10000, "nodes": ["vin", "n_inv"]},
    {"ref": "Rf", "value_ohms": 47000, "nodes": ["vout", "n_inv"]}
  ],
  "detected_topology": "op_amp_inverting",
  "computed": {"gain": -4.7}
}
```

Implementation notes:

- Use regex to detect resistor lines.
- For MVP, parse known labels `Rin`, `Rf`, or infer resistors connected to `vin`, `vout`, and `n_inv`.
- Do not try full SPICE parsing.

### Tool 2: `analyze_waveform_csv`

Input:

```json
{"path": "observed_saturated_waveform.csv"}
```

Output:

```json
{
  "v_min": 11.2,
  "v_max": 12.0,
  "mean": 11.7,
  "is_saturated": true,
  "saturation_rail": "positive",
  "frequency_estimate_hz": null
}
```

Implementation notes:

- Use pandas.
- Expected columns: `time_s`, `vin_v`, `vout_v`.
- If `vout_v` stays near +12, classify saturation.

### Tool 3: `compare_expected_vs_observed`

Input:

```json
{
  "expected_gain": -4.7,
  "observed_summary": {"is_saturated": true, "saturation_rail": "positive"},
  "measurements": []
}
```

Output:

```json
{
  "mismatch_type": "saturation_instead_of_linear_amplification",
  "likely_fault_categories": ["reference_input", "feedback", "power_rails", "common_ground"],
  "recommended_next_measurement": "non_inverting_input_voltage"
}
```

### Tool 4: `safety_check`

Input:

```json
{"text": "My circuit uses 230V AC"}
```

Output:

```json
{
  "risk_level": "high_voltage_or_mains",
  "allowed": false,
  "message": "CircuitSage is for low-voltage educational circuits. Stop and ask an instructor before debugging mains-powered circuits."
}
```

### Tool 5: `retrieve_lab_manual`

MVP implementation:

- Read `lab_manual_excerpt.md` and do simple keyword matching.
- Later replace with FAISS/Chroma embeddings.

Output:

```json
{
  "snippets": [
    {
      "source": "lab_manual_excerpt.md",
      "text": "For an inverting amplifier, the non-inverting terminal must be tied to ground..."
    }
  ]
}
```

### Tool 6: `generate_report`

Use either template + Gemma or deterministic template.

Output:

```markdown
# Lab Reflection: Inverting Op-Amp Amplifier

## Expected behavior
...

## Observed issue
...

## Diagnosis
...

## What I learned
...

## Viva questions
...
```

---

## 12. Agent orchestration

### Main diagnosis algorithm

Pseudocode:

```python
def diagnose_session(session_id, user_message=None):
    session = load_session(session_id)
    artifacts = load_artifacts(session_id)
    measurements = load_measurements(session_id)

    safety = safety_check(user_message + artifacts_text + measurements_text)
    if not safety.allowed:
        return safety_response(safety)

    netlist_result = parse_netlist_if_available(artifacts)
    waveform_result = analyze_waveform_if_available(artifacts)
    manual_snippets = retrieve_lab_manual(session, query=user_message)
    comparison = compare_expected_vs_observed(netlist_result, waveform_result, measurements)

    context = build_agent_context(
        session=session,
        netlist=netlist_result,
        waveform=waveform_result,
        measurements=measurements,
        manual_snippets=manual_snippets,
        comparison=comparison,
        user_message=user_message,
    )

    llm_result = call_gemma_for_structured_diagnosis(context)
    diagnosis = merge_tool_results_with_llm(llm_result, comparison, safety)
    save_diagnosis(session_id, diagnosis)
    return diagnosis
```

### Agent behavior requirements

CircuitSage must:

- Ask for the next measurement when evidence is incomplete.
- Avoid pretending it can see exact wiring unless image analysis confirms it.
- Show evidence used.
- Distinguish simulation correctness from physical wiring faults.
- Prefer debugging sequence over direct final answer.
- Keep explanations educational.
- Always include safety warnings for high voltage, mains, hot components, capacitors, and power-off-before-rewiring.

CircuitSage must not:

- Give mains debugging instructions.
- Claim certainty from blurry photos.
- Tell students to randomly replace parts.
- Output huge generic theory dumps.
- Act like a perfect repair expert.

---

## 13. Prompt templates

### System prompt for CircuitSage

```text
You are CircuitSage, a local-first AI lab partner for electrical and electronics students.

Your job is to help students debug low-voltage educational circuits by connecting theory, simulation, and bench measurements.

You are not a generic chatbot. You behave like a patient lab teaching assistant.

Rules:
1. First understand the expected circuit behavior from the lab manual, netlist, waveform, and measurements.
2. Compare expected behavior with observed behavior.
3. Ask for the next most useful measurement instead of guessing.
4. Explain why that measurement matters.
5. Give short, practical steps the student can perform safely.
6. Include safety warnings. Refuse detailed live debugging for mains/high-voltage circuits.
7. Be honest about uncertainty, especially with images.
8. Teach the underlying concept after the immediate debug step.
9. Output structured JSON when requested.

Tone: encouraging, clear, non-judgmental, practical.
```

### Structured diagnosis prompt

```text
Given the following lab context, produce a structured diagnosis.

Return valid JSON matching this schema:
{
  "experiment_type": string,
  "expected_behavior": object,
  "observed_behavior": object,
  "likely_faults": [{"fault": string, "confidence": number, "why": string}],
  "next_measurement": {"label": string, "expected": string, "instruction": string},
  "safety": {"risk_level": string, "warnings": [string]},
  "student_explanation": string,
  "confidence": "low" | "medium" | "medium_high" | "high"
}

Lab context:
{context}
```

### Chat response prompt

```text
The student asked: {user_message}

Context:
{context}

Write a helpful bench-mode response in this format:

1. What I think is happening
2. What to measure next
3. Expected value
4. Why this matters
5. Safety note

Keep it short and practical. Do not overload the student with generic theory.
```

### Report prompt

```text
Generate a post-lab reflection for an EEE student.

Include:
- Aim of experiment
- Expected behavior
- Observed issue
- Debugging steps taken
- Root cause
- Corrected concept
- Simulation vs hardware comparison
- 5 viva questions with concise answers
- Personal mistake memory note

Context:
{context}
```

---

## 14. Frontend screens

### Home page

Purpose: list sessions and create new session.

Components:

- New Lab Session button.
- Session cards.
- Demo seed session button: “Load Op-Amp Demo.”

### Studio page

Route:

```text
/studio/:sessionId
```

Sections:

1. Header
   - Session title/status.
   - Start Bench Mode button.
   - Generate Report button.

2. Left column: Artifacts
   - Upload manual.
   - Upload netlist.
   - Upload waveform CSV.
   - Upload image.
   - Show file list.

3. Middle column: Session context
   - Expected gain.
   - Observed measurements.
   - Current diagnosis.
   - Tool call timeline.

4. Right column: Agent
   - Message input.
   - Chat/diagnosis output.
   - Next measurement card.

### Bench page

Route:

```text
/bench/:sessionId
```

Mobile-first layout:

- Session title.
- Camera/image upload button.
- Measurement form.
- Voice/text question input.
- “Ask what to measure next” button.
- Latest diagnosis card.

Measurement form fields:

- Label: `Vout`, `V+`, `V-`, `non-inverting input`, `feedback node`.
- Value.
- Unit.
- Mode: DC/AC/peak/peak-to-peak.
- Notes.

### Report page/panel

Shows generated Markdown and copy/download button.

---

## 15. Demo seed behavior

The app must include a seeded session that works immediately.

### Seed session title

```text
Op-Amp Inverting Amplifier: Why is my output stuck at +12V?
```

### Seed artifacts

- Netlist with Rin = 10k, Rf = 47k.
- Expected waveform CSV.
- Observed saturated waveform CSV.
- Lab manual excerpt.
- Placeholder oscilloscope image.

### Seed measurements

```json
[
  {"label": "Vout", "value": 11.8, "unit": "V", "mode": "DC", "context": "Output stuck near positive rail"},
  {"label": "V+", "value": 12.1, "unit": "V", "mode": "DC", "context": "Positive supply rail"},
  {"label": "V-", "value": -12.0, "unit": "V", "mode": "DC", "context": "Negative supply rail"}
]
```

### Expected diagnosis

```text
The simulation expects gain around -4.7, but the observed output is saturated near the positive rail. Since both supply rails look correct, the next best measurement is the non-inverting input voltage. It should be near 0V. If it is floating or not tied to ground, the op-amp can saturate even if the resistor values are correct.
```

### After user enters `V_noninv = 2.8V`

CircuitSage should say:

```text
That confirms the likely issue: the non-inverting input is not at the 0V reference. Power off, connect the non-inverting input to circuit ground, and retest. This is a reference/feedback problem, not a gain-formula problem.
```

---

## 16. Safety policy

CircuitSage is an educational low-voltage assistant.

### Always allowed

- Battery-powered circuits.
- Low-voltage op-amp labs.
- RC filters.
- voltage dividers.
- Arduino/Tinkercad circuits.
- signal generator + oscilloscope educational circuits.

### Caution

- Capacitors that may hold charge.
- power supplies above 24V.
- hot components.
- unknown wiring.

### Refuse detailed live instructions

If the user mentions:

- mains,
- 110V/230V AC,
- wall outlet,
- transformer primary,
- SMPS primary side,
- CRT/flyback,
- microwave oven,
- EV battery pack,
- large capacitor bank.

Response style:

```text
CircuitSage is only for low-voltage educational circuits. This may involve dangerous voltage/current. Power down and ask an instructor or qualified technician. I can help you understand the theory or review a de-energized schematic, but I cannot guide live debugging of this circuit.
```

---

## 17. Implementation phases

### Phase 1: Backend skeleton

Acceptance criteria:

- FastAPI app runs.
- SQLite DB works.
- Can create/list/get session.
- Can upload artifacts.
- Can add measurements.
- Can return seeded demo session.

### Phase 2: Deterministic tools

Acceptance criteria:

- `parse_netlist` computes gain = -4.7 from sample netlist.
- `analyze_waveform_csv` detects expected vs saturated waveform.
- `compare_expected_vs_observed` returns mismatch category.
- `safety_check` catches mains/high voltage.

### Phase 3: Ollama/Gemma client

Acceptance criteria:

- Reads `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
- Calls `/api/generate` or `/api/chat`.
- Has graceful fallback if Ollama is unavailable.
- Logs prompt and response for debugging.

Fallback behavior:

- If Ollama is not running, return deterministic diagnosis so demo still works.
- UI should show “Gemma unavailable; using deterministic fallback” only in dev mode.

### Phase 4: Agent orchestrator

Acceptance criteria:

- Builds context from session/artifacts/measurements.
- Calls tools.
- Calls Gemma.
- Saves diagnosis.
- Returns structured response.

### Phase 5: Frontend Studio

Acceptance criteria:

- Create/load seeded session.
- Upload files.
- View artifacts/measurements.
- Run diagnosis.
- Show diagnosis card and next measurement.

### Phase 6: Mobile Bench Mode

Acceptance criteria:

- QR opens session on phone.
- Phone uploads image.
- Phone adds measurement.
- Phone asks “what should I measure next?”
- PC session reflects mobile data.

### Phase 7: Report generation

Acceptance criteria:

- Generates Markdown lab reflection.
- Includes expected behavior, observed behavior, diagnosis, learning note, viva questions.

### Phase 8: Polish

Acceptance criteria:

- Good UI.
- Demo seed button.
- Screenshots.
- README.
- Short install/run instructions.
- Video script in docs.

---

## 18. Sample backend code contracts

### `backend/app/services/ollama_client.py`

```python
class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, messages: list[dict], format_json: bool = False) -> str:
        """Call Ollama chat endpoint. Raise a clean error if unavailable."""
        ...
```

### `backend/app/tools/parse_netlist.py`

```python
def parse_netlist_text(text: str) -> dict:
    """Parse a tiny subset of SPICE-like netlists for demo circuits."""
    ...
```

### `backend/app/tools/waveform_analysis.py`

```python
def analyze_waveform_csv(path: str) -> dict:
    """Analyze CSV columns time_s, vin_v, vout_v."""
    ...
```

### `backend/app/services/agent_orchestrator.py`

```python
async def diagnose_session(session_id: str, user_message: str | None = None) -> dict:
    """Main workflow: load context -> tools -> Gemma -> save diagnosis."""
    ...
```

---

## 19. README content required

The repository README should include:

1. What CircuitSage is.
2. The story: “Software students get stack traces. Electronics students get silence.”
3. Demo GIF/screenshots.
4. Architecture diagram.
5. How Gemma 4 is used.
6. Local setup:

```bash
# backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# frontend
cd frontend
npm install
npm run dev
```

7. Ollama setup:

```bash
ollama serve
ollama pull <gemma-4-model-tag>
export OLLAMA_MODEL=<gemma-4-model-tag>
```

8. Demo flow:

```text
1. Load Op-Amp Demo.
2. Start Bench Mode.
3. Open phone QR.
4. Upload/enter saturated output.
5. Run diagnosis.
6. Enter non-inverting input measurement.
7. Generate report.
```

9. Safety disclaimer.
10. Hackathon tracks.

---

## 20. Video story

### Title

**CircuitSage — Stack traces for circuits**

### 3-minute structure

#### 0:00–0:20 Hook

Visual:

- Show code error: `SyntaxError`.
- Cut to breadboard + flat/saturated oscilloscope.

Voiceover:

> When software fails, it gives you an error. When a circuit fails, it gives you silence.

#### 0:20–0:45 Problem

Visual:

- Student in crowded electronics lab.
- Lab instructor busy.
- Student has LTspice simulation working but hardware failing.

Voiceover:

> Electronics students are expected to move from theory, to simulation, to hardware. But the hardest part is the gap between a perfect simulation and a messy physical circuit.

#### 0:45–1:15 PC Studio

Visual:

- CircuitSage Studio loads lab manual, netlist, waveform.
- It computes expected gain.

Voiceover:

> CircuitSage starts before the lab. It understands the experiment, checks the simulation, and predicts what the student should measure.

#### 1:15–1:55 Mobile Bench Mode

Visual:

- Student scans QR.
- Phone uploads oscilloscope image/measurement.
- Bench Mode asks for next measurement.

Voiceover:

> In the lab, the phone becomes CircuitSage’s eyes. It remembers the simulation and guides the next measurement.

#### 1:55–2:25 Diagnosis

Visual:

- Tool calls shown.
- Diagnosis card shown.

JSON visual:

```json
{
  "expected_gain": -4.7,
  "observed_output": "positive saturation",
  "next_measurement": "non-inverting input voltage",
  "likely_fault": "floating reference input"
}
```

Voiceover:

> It does not just guess. It compares expected behavior with measured behavior and builds a debugging path.

#### 2:25–2:45 Fix

Visual:

- Student connects non-inverting input to ground.
- Output waveform becomes correct.

Voiceover:

> The circuit works. More importantly, the student understands why.

#### 2:45–3:00 Vision

Visual:

- Report generation.
- Mistake memory.
- Future circuits.

Voiceover:

> CircuitSage is not replacing teachers. It gives every student a patient lab partner — one that runs locally, remembers their circuit, and helps them become a hardware builder.

Final card:

```text
CircuitSage
Stack traces for circuits.
```

---

## 21. Kaggle writeup outline

Target under 1,500 words.

### Title

CircuitSage: Stack Traces for Circuits

### Subtitle

An offline Gemma-powered lab partner that follows electronics students from simulation to oscilloscope.

### Sections

1. **Problem**
   - Software errors are visible; circuit failures are silent.
   - Practical electronics mentorship does not scale.

2. **Solution**
   - PC Studio + mobile Bench Mode.
   - Persistent lab session memory.
   - Gemma agent connects simulation, lab manual, measurements, images.

3. **Demo**
   - Op-amp inverting amplifier.
   - Simulation expects gain -4.7.
   - Bench output saturates.
   - CircuitSage asks next measurement and diagnoses missing reference ground.

4. **How Gemma 4 is used**
   - Local reasoning through Ollama.
   - Multimodal input for bench images.
   - Tool/function orchestration.
   - Grounded lab-manual retrieval.
   - Structured JSON diagnosis.

5. **Architecture**
   - FastAPI backend.
   - React/Next PWA.
   - SQLite memory.
   - deterministic circuit tools.
   - Ollama Gemma interface.

6. **Impact**
   - Scales lab mentorship.
   - Helps under-resourced labs.
   - Encourages hardware builders.
   - Bridges theory/simulation/hardware.

7. **Safety & Trust**
   - low-voltage only.
   - evidence display.
   - uncertainty handling.
   - asks for measurements before conclusions.

8. **Future work**
   - more circuits.
   - real LTspice/MATLAB integration.
   - Tinkercad/Arduino support.
   - Cactus/LiteRT mobile routing.
   - Unsloth fine-tuned fault diagnosis.

---

## 22. Design principles

### Build a workflow, not a chatbot

The app should feel like a lab assistant that persists across time.

### The next measurement is the product

The killer UX is not “explain op-amps.” It is:

> “Measure pin 3. Expected: 0V. Here is why.”

### Show evidence

Every diagnosis should cite session evidence:

- netlist values,
- expected gain,
- waveform behavior,
- measurements,
- lab manual snippet.

### Admit uncertainty

Especially for images:

> “The breadboard photo is not clear enough to confirm the feedback path. Please send a top-down photo or measure continuity from output to Rf.”

### Keep safety visible

Safety warnings make the tool more credible.

---

## 23. Optional stretch: Fault Lab

Fault Lab is a practice mode inspired by clinical simulation tools.

Instead of AI patients, CircuitSage gives AI circuit cases.

Example:

```text
Case: Bridge Rectifier Mystery
Symptoms:
- Transformer secondary: 12.1V AC
- DC output: 1.1V
- Capacitor warming
- Diode D3 orientation uncertain
Task:
Choose the next measurement and diagnose the fault.
```

CircuitSage grades:

```text
Good: You verified the input source first.
Missed: You should check diode orientation before replacing the capacitor.
Next time: follow source -> rectifier -> filter -> load.
```

This can be a powerful post-MVP feature but should not block the core demo.

---

## 24. Optional stretch: broader circuit support

After op-amp demo works, add:

1. Voltage divider
2. RC low-pass filter
3. Bridge rectifier
4. BJT common-emitter amplifier
5. Arduino LED/sensor circuit from Tinkercad

Each circuit needs:

- expected behavior function,
- common fault list,
- next-measurement decision tree,
- sample demo data.

---

## 25. Agent task decomposition

Give Claude Code/Codex these tasks one at a time.

### Task 1: Create project skeleton

```text
Create the CircuitSage monorepo exactly as described in SPEC.md. Build a FastAPI backend and React/Vite frontend. Add a README and sample_data directory. Do not implement full functionality yet; just make both apps run.
```

### Task 2: Implement backend models and API

```text
Implement SQLite-backed LabSession, Artifact, Measurement, Diagnosis, and Message models. Add CRUD endpoints for sessions, uploads, measurements, and diagnoses. Add seed endpoint for the op-amp demo.
```

### Task 3: Implement deterministic circuit tools

```text
Implement parse_netlist, analyze_waveform_csv, compare_expected_vs_observed, safety_check, retrieve_lab_manual, and generate_report. Add tests with sample_data/op_amp_lab.
```

### Task 4: Implement Ollama client

```text
Implement an Ollama client configurable by OLLAMA_BASE_URL and OLLAMA_MODEL. Add graceful fallback if Ollama is unavailable. Add a simple /api/health/model endpoint.
```

### Task 5: Implement diagnosis orchestrator

```text
Implement diagnose_session(session_id, user_message). It should load session context, run safety check, run deterministic tools, build a prompt, call Gemma via Ollama, parse JSON, save the diagnosis, and return a structured response.
```

### Task 6: Build Studio UI

```text
Build the PC Studio page with session overview, upload panel, measurements list, diagnosis panel, tool-call timeline, and report panel. Make the seeded op-amp demo usable with one click.
```

### Task 7: Build Bench Mode UI

```text
Build mobile-friendly Bench Mode at /bench/:sessionId. Include image upload, measurement entry, text question, latest diagnosis, and next measurement card.
```

### Task 8: QR pairing

```text
Add Start Bench Mode button in Studio. Generate QR code linking to /bench/:sessionId. Ensure phone on same network can connect if backend/frontend host is reachable.
```

### Task 9: Report generation

```text
Add Generate Report button. Use session context and diagnosis to create a Markdown report with aim, expected behavior, observations, diagnosis, learning note, error analysis, and viva questions.
```

### Task 10: Polish demo

```text
Improve UI copy, add screenshots/placeholders, add safety badges, add README demo instructions, and ensure the op-amp demo works from clean install.
```

---

## 26. Quality gates

Before submission, verify:

- Fresh clone can run backend and frontend.
- Demo seed works without external paid APIs.
- App can run without internet after dependencies/model are installed.
- Ollama model name is configurable.
- If Ollama is unavailable, deterministic fallback still demonstrates workflow.
- README is clear.
- Code has comments around Gemma integration.
- Safety refusal works for mains/high voltage.
- 3-minute video can be recorded from actual UI.
- Public repo contains sample data, not private personal data.

---

## 27. Minimal sample data content

### `lab_manual_excerpt.md`

```markdown
# Inverting Op-Amp Amplifier Lab

Aim: Verify that an inverting op-amp amplifier produces an output voltage Vout = -(Rf/Rin) Vin.

For this lab, use Rin = 10kΩ and Rf = 47kΩ. The expected gain is -4.7.

The non-inverting input must be connected to circuit ground. With negative feedback, the inverting input behaves like a virtual ground.

Before debugging gain, check:
1. Positive and negative supply rails.
2. Common ground between function generator, oscilloscope, and circuit.
3. Non-inverting input connected to ground.
4. Feedback resistor connected between output and inverting input.

If the output saturates near a supply rail, likely causes include missing feedback, floating input reference, incorrect op-amp power pins, or input amplitude too large.
```

### `opamp_inverting.net`

```spice
* Inverting Op-Amp Amplifier Demo
Vin vin 0 SIN(0 1 1k)
Rin vin n_inv 10k
Rf vout n_inv 47k
* ideal op amp placeholder
Eop vout 0 0 n_inv 100000
VCC vcc 0 DC 12
VEE vee 0 DC -12
.tran 0 5m 0 10u
.end
```

### `student_question.txt`

```text
My LTspice simulation looks correct, but in the lab my op-amp output is stuck near +12V. What should I check first?
```

---

## 28. Final product wording

Use this wording in README, demo, and writeup:

> CircuitSage is not replacing teachers. It gives every student a patient lab partner — one that can see the circuit, remember the simulation, ask for the next measurement, and explain the mistake.

> Software students get stack traces. Electronics students get silence. CircuitSage gives circuits a debugging voice.

---

## 29. Final answer to “what are we building?”

We are building a persistent PC + mobile workflow for electronics labs:

```text
PC Studio:
- understands lab manual, simulation, netlist, MATLAB/CSV plots
- stores the session memory
- runs Gemma + tools

Mobile Bench Mode:
- captures oscilloscope/multimeter/breadboard evidence
- lets the student ask questions at the bench
- syncs with the PC session

Gemma Agent:
- compares simulation vs measured behavior
- calls deterministic circuit tools
- asks for the next measurement
- diagnoses likely faults
- generates a learning report
```

The MVP is the op-amp lab. The story is global practical engineering education. The demo is simulation -> silent hardware failure -> CircuitSage next measurement -> diagnosis -> fix -> reflection.

