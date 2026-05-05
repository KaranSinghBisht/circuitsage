from __future__ import annotations

import base64
import io
import json
import shutil
import uuid
from pathlib import Path
from typing import Annotated

import qrcode
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .config import get_settings
from .database import db, init_db, read_text_excerpt, row_to_dict, rows_to_dicts, utc_now
from .schemas import (
    ChatRequest,
    CompanionAnalyzeRequest,
    DiagnosisRequest,
    LabSessionCreate,
    LabSessionUpdate,
    MeasurementCreate,
)
from .services.agent_orchestrator import build_report, diagnose_session
from .services.fault_catalog import CATALOG
from .services.ollama_client import OllamaClient, parse_json_response
from .tools.parse_netlist import parse_netlist_file
from .tools.report_builder import generate_report_pdf
from .tools.safety_check import safety_check
from .tools.schematic_to_netlist import image_file_to_base64, recognize_schematic


app = FastAPI(title="CircuitSage API", version="0.1.0")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


def _get_session_or_404(session_id: str) -> dict:
    with db() as conn:
        session = row_to_dict(conn.execute("SELECT * FROM lab_sessions WHERE id = ?", (session_id,)).fetchone())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _get_artifact_or_404(artifact_id: str) -> dict:
    with db() as conn:
        artifact = row_to_dict(conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone())
    if not artifact or not Path(artifact["path"]).exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


def _artifact_kind(filename: str, provided: str | None = None) -> str:
    if provided:
        return provided
    suffix = Path(filename).suffix.lower()
    if suffix in {".md", ".txt", ".pdf"}:
        return "manual"
    if suffix in {".net", ".cir"}:
        return "netlist"
    if suffix == ".csv":
        return "waveform_csv"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        lowered = filename.lower()
        if "breadboard" in lowered:
            return "breadboard"
        if "scope" in lowered or "oscilloscope" in lowered:
            return "oscilloscope"
        return "image"
    if suffix in {".wav", ".caf", ".m4a", ".mp3", ".aac"}:
        return "audio"
    if suffix == ".m":
        return "matlab"
    if suffix == ".ino":
        return "tinkercad_code"
    return "note"


def _insert_artifact(session_id: str, kind: str, source_path: Path, filename: str | None = None) -> dict:
    artifact_id = str(uuid.uuid4())
    filename = filename or source_path.name
    safe_dir = settings.upload_dir / session_id
    safe_dir.mkdir(parents=True, exist_ok=True)
    dest = safe_dir / f"{artifact_id}_{filename}"
    if source_path.resolve() != dest.resolve():
        shutil.copyfile(source_path, dest)
    excerpt = read_text_excerpt(dest)
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO artifacts (id, session_id, kind, filename, path, text_excerpt, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, session_id, kind, filename, str(dest), excerpt, "{}", now),
        )
        row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    return row_to_dict(row)


def _decode_data_url(data_url: str | None) -> bytes | None:
    if not data_url:
        return None
    try:
        payload = data_url.split(",", 1)[1] if "," in data_url else data_url
        return base64.b64decode(payload)
    except Exception:
        return None


def _image_base64_from_data_url(data_url: str | None) -> str | None:
    if not data_url:
        return None
    return data_url.split(",", 1)[1] if "," in data_url else data_url


def _guess_workspace(app_hint: str, question: str) -> str:
    text = f"{app_hint} {question}".lower()
    if "tinkercad" in text or "arduino" in text:
        return "tinkercad"
    if "ltspice" in text or "spice" in text or ".tran" in text or ".op" in text:
        return "ltspice"
    if "matlab" in text or "simulink" in text or "plot" in text or ".m" in text:
        return "matlab"
    return "electronics_workspace"


def _save_companion_snapshot(session_id: str, image_bytes: bytes) -> dict:
    _get_session_or_404(session_id)
    artifact_id = str(uuid.uuid4())
    safe_dir = settings.upload_dir / session_id
    safe_dir.mkdir(parents=True, exist_ok=True)
    dest = safe_dir / f"{artifact_id}_companion_snapshot.jpg"
    dest.write_bytes(image_bytes)
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO artifacts (id, session_id, kind, filename, path, text_excerpt, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                session_id,
                "image",
                "companion_snapshot.jpg",
                str(dest),
                "",
                json.dumps({"source": "companion_screen"}),
                now,
            ),
        )
        row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    return row_to_dict(row)


def _companion_fallback(question: str, workspace: str, has_image: bool, safety: dict) -> dict:
    workspace_labels = {
        "tinkercad": "Tinkercad / Arduino circuit workspace",
        "ltspice": "LTspice schematic or waveform workspace",
        "matlab": "MATLAB / Simulink analysis workspace",
        "electronics_workspace": "electronics workspace",
    }
    next_steps = {
        "tinkercad": [
            "Check that every component shares the same ground node.",
            "Verify polarity and pin order before changing values.",
            "Run the simulation and compare the measured node with the expected node.",
        ],
        "ltspice": [
            "Run an operating-point check before judging the transient plot.",
            "Confirm source amplitude, net labels, ground reference, and rail connections.",
            "Probe the input, output, and reference node in the same plot window.",
        ],
        "matlab": [
            "Check units, sample rate, and column names before interpreting the plot.",
            "Compare expected gain or transfer function against measured arrays.",
            "Print min, max, mean, and saturation/clipping checks for the signal.",
        ],
        "electronics_workspace": [
            "Identify expected behavior, observed behavior, and the exact node being measured.",
            "Measure supply rails and ground reference before replacing parts.",
            "Ask for the next most informative measurement, not a broad theory answer.",
        ],
    }
    return {
        "mode": "deterministic_fallback",
        "workspace": workspace,
        "visible_context": (
            "A screenshot frame was captured, but local visual reasoning needs a vision-capable Gemma/Ollama model."
            if has_image
            else "No screen frame was included. Start screen watch or attach a screenshot."
        ),
        "answer": (
            f"I am treating this as a {workspace_labels[workspace]}. "
            "Tell me the exact symptom or hit Analyze Current Screen after sharing the relevant window."
        ),
        "next_actions": next_steps[workspace],
        "can_click": False,
        "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
        "confidence": "low" if has_image else "low_no_image",
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "CircuitSage"}


@app.get("/api/health/model")
async def model_health() -> dict:
    return await OllamaClient(settings.ollama_base_url, settings.ollama_model).health()


@app.post("/api/tools/schematic-to-netlist")
async def schematic_to_netlist_endpoint(
    file: UploadFile | None = File(default=None),
    artifact_id: str | None = Form(default=None),
) -> dict:
    if artifact_id:
        artifact = _get_artifact_or_404(artifact_id)
        image_b64 = image_file_to_base64(artifact["path"])
        return await recognize_schematic(image_b64, hint=artifact.get("filename", ""))
    if file:
        payload = await file.read()
        image_b64 = base64.b64encode(payload).decode("ascii")
        return await recognize_schematic(image_b64, hint=Path(file.filename or "").name)
    raise HTTPException(status_code=400, detail="file or artifact_id required")


@app.post("/api/companion/analyze")
async def companion_analyze(payload: CompanionAnalyzeRequest) -> dict:
    safety = safety_check(payload.question)
    image_bytes = _decode_data_url(payload.image_data_url)
    image_base64 = _image_base64_from_data_url(payload.image_data_url)
    workspace = _guess_workspace(payload.app_hint, payload.question)
    saved_artifact = None

    if payload.session_id and payload.save_snapshot and image_bytes:
        saved_artifact = _save_companion_snapshot(payload.session_id, image_bytes)

    if not safety["allowed"]:
        return {
            "mode": "safety_refusal",
            "workspace": workspace,
            "visible_context": "Screen analysis stopped because high-voltage or mains risk was mentioned.",
            "answer": safety["message"],
            "next_actions": ["Power down and ask an instructor or qualified technician."],
            "can_click": False,
            "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
            "confidence": "high",
            "saved_artifact": saved_artifact,
        }

    fallback = _companion_fallback(payload.question, workspace, bool(image_base64), safety)
    prompt = f"""
You are CircuitSage Companion, an always-on local lab buddy for electronics students.

You are looking at a screenshot from a student's active workspace. The workspace may be Tinkercad, LTspice, MATLAB, Simulink, a browser lab manual, a waveform plot, or a circuit simulator.

Student question:
{payload.question or "No explicit question. Inspect the screen and suggest what to check next."}

App hint:
{payload.app_hint}

Requested language:
{payload.lang}

Return compact JSON:
{{
  "workspace": "tinkercad | ltspice | matlab | electronics_workspace | unknown",
  "visible_context": "what you can actually see, with uncertainty",
  "answer": "direct help for the student",
  "next_actions": ["short concrete step", "short concrete step", "short concrete step"],
  "can_click": false,
  "safety": {{"risk_level": "low_voltage_lab | high_voltage_or_mains", "warnings": ["..."]}},
  "confidence": "low | medium | high"
}}

Rules:
- Do not claim you can see details that are not visible.
- For LTspice, focus on net labels, ground, source settings, rails, and waveform probes.
- For MATLAB, focus on plots, units, arrays, sample rate, transfer functions, and numerical checks.
- For Tinkercad, focus on wiring, pin order, ground, polarity, code/simulation mismatch, and measured nodes.
- If evidence is incomplete, ask for the next measurement or the next screen to inspect.
- Keep JSON keys in English. Translate user-facing explanation, next actions, and warnings to the requested language.
- Refuse detailed live debugging for mains/high-voltage.
"""
    if not image_base64:
        return {**fallback, "saved_artifact": saved_artifact}

    try:
        vision_result = await OllamaClient(settings.ollama_base_url, settings.ollama_vision_model).chat(
            [
                {
                    "role": "user",
                    "content": f"{prompt}\n\nFirst describe the visible screen evidence and next actions in plain text.",
                    "images": [image_base64],
                }
            ],
            format_json=False,
        )
        vision_text = vision_result["content"]
        structure_prompt = f"""
Convert this CircuitSage Companion vision analysis into the required compact JSON schema.

Original student question:
{payload.question}

Vision analysis:
{vision_text}

Return only JSON with keys:
workspace, visible_context, answer, next_actions, can_click, safety, confidence
"""
        structured_result = await OllamaClient(settings.ollama_base_url, settings.ollama_vision_model).chat(
            [{"role": "user", "content": structure_prompt}],
            format_json=True,
        )
        result = structured_result["content"]
        parsed = parse_json_response(result)
        if not parsed:
            return {**fallback, "mode": "gemma_text_unparsed", "raw": result[:1200], "saved_artifact": saved_artifact}
        parsed.setdefault("mode", "ollama_gemma_vision")
        parsed.setdefault("can_click", False)
        parsed.setdefault("saved_artifact", saved_artifact)
        return parsed
    except Exception as exc:  # noqa: BLE001 - fallback is required when Ollama is missing.
        return {
            **fallback,
            "mode": "deterministic_fallback",
            "gemma_error": f"{exc.__class__.__name__}: {exc}",
            "saved_artifact": saved_artifact,
        }


@app.post("/api/sessions")
def create_session(payload: LabSessionCreate) -> dict:
    session_id = str(uuid.uuid4())
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO lab_sessions (id, title, student_level, experiment_type, status, created_at, updated_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                payload.title,
                payload.student_level,
                payload.experiment_type,
                "pre_lab",
                now,
                now,
                payload.notes,
            ),
        )
        row = conn.execute("SELECT * FROM lab_sessions WHERE id = ?", (session_id,)).fetchone()
    return row_to_dict(row)


@app.get("/api/sessions")
def list_sessions() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM lab_sessions ORDER BY updated_at DESC").fetchall()
    return rows_to_dicts(rows)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = _get_session_or_404(session_id)
    with db() as conn:
        artifacts = rows_to_dicts(conn.execute("SELECT * FROM artifacts WHERE session_id = ?", (session_id,)).fetchall())
        measurements = rows_to_dicts(
            conn.execute("SELECT * FROM measurements WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall()
        )
        diagnoses = rows_to_dicts(
            conn.execute("SELECT * FROM diagnoses WHERE session_id = ? ORDER BY created_at DESC", (session_id,)).fetchall()
        )
        report = row_to_dict(conn.execute("SELECT * FROM reports WHERE session_id = ?", (session_id,)).fetchone())
    return {
        **session,
        "artifacts": artifacts,
        "measurements": measurements,
        "diagnoses": diagnoses,
        "latest_diagnosis": diagnoses[0]["diagnosis_json"] if diagnoses else None,
        "report": report["markdown"] if report else "",
    }


@app.patch("/api/sessions/{session_id}")
def update_session(session_id: str, payload: LabSessionUpdate) -> dict:
    _get_session_or_404(session_id)
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        columns = ", ".join(f"{key} = ?" for key in updates)
        values = [*updates.values(), utc_now(), session_id]
        with db() as conn:
            conn.execute(f"UPDATE lab_sessions SET {columns}, updated_at = ? WHERE id = ?", values)
    return _get_session_or_404(session_id)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    _get_session_or_404(session_id)
    with db() as conn:
        conn.execute("DELETE FROM lab_sessions WHERE id = ?", (session_id,))
    return {"deleted": True}


@app.post("/api/sessions/seed/op-amp")
async def seed_op_amp_demo() -> dict:
    return await _seed_demo(
        topology="op_amp_inverting",
        title="Op-Amp Inverting Amplifier: Why is my output stuck at +12V?",
        notes="Seeded hackathon demo: simulation is correct, bench output is saturated near +12 V.",
        sample_dir=settings.sample_data_dir,
        samples=[
            ("manual", "lab_manual_excerpt.md"),
            ("netlist", "opamp_inverting.net"),
            ("waveform_csv", "expected_waveform.csv"),
            ("waveform_csv", "observed_saturated_waveform.csv"),
            ("note", "student_question.txt"),
            ("oscilloscope", "scope_saturated_placeholder.png"),
            ("breadboard", "breadboard_disconnected.png"),
            ("oscilloscope", "fixed_scope_placeholder.png"),
        ],
        measurements=[
            MeasurementCreate(label="Vout", value=11.8, unit="V", mode="DC", context="Output stuck near positive rail"),
            MeasurementCreate(label="V+", value=12.1, unit="V", mode="DC", context="Positive supply rail"),
            MeasurementCreate(label="V-", value=-12.0, unit="V", mode="DC", context="Negative supply rail"),
        ],
        question="My output is stuck near +12V. What should I check first?",
    )


@app.get("/api/faults")
def list_fault_catalog() -> list[dict]:
    rows: list[dict] = []
    for topology, catalog in sorted(CATALOG.items()):
        if topology == "unknown":
            continue
        for fault in catalog.get("faults", []):
            rows.append(
                {
                    "topology": topology,
                    "id": fault["id"],
                    "name": fault["name"],
                    "why": fault["why"],
                    "requires_measurements": fault.get("requires_measurements", []),
                    "verification_test": fault.get("verification_test", ""),
                    "fix_recipe": fault.get("fix_recipe", ""),
                    "thumbnail_before": "sample_data/op_amp_lab/scope_saturated_placeholder.png",
                    "thumbnail_after": "sample_data/op_amp_lab/fixed_scope_placeholder.png",
                }
            )
    return rows


@app.post("/api/sessions/seed/fault/{topology}/{fault_id}")
async def seed_fault_demo(topology: str, fault_id: str) -> dict:
    catalog = CATALOG.get(topology)
    if not catalog:
        raise HTTPException(status_code=404, detail="Topology not found")
    fault = next((item for item in catalog.get("faults", []) if item["id"] == fault_id), None)
    if not fault:
        raise HTTPException(status_code=404, detail="Fault not found")
    sample_dir = settings.sample_data_dir.parent / topology
    if topology == "op_amp_inverting" and not sample_dir.exists():
        sample_dir = settings.sample_data_dir
    samples = []
    for filename in ("lab_manual_excerpt.md", "netlist.net", "opamp_inverting.net", "expected_waveform.csv", "observed_saturated_waveform.csv", "observed_loaded.csv", "observed_attenuated.csv", "observed_unity_gain.csv", "observed_saturated.csv", "student_question.txt"):
        if (sample_dir / filename).exists():
            kind = _artifact_kind(filename)
            if filename.startswith("observed") or filename.startswith("expected"):
                kind = "waveform_csv"
            samples.append((kind, filename))
    measurement_key = (fault.get("requires_measurements") or ["observed_node"])[0]
    signature = fault.get("signature", {})
    value = float(signature.get("value", 1.0))
    if signature.get("operator") in {"abs_gt", "gt", "gte"}:
        value = max(value + 0.7, 1.0)
    measurements = [MeasurementCreate(label=measurement_key, value=value, unit="V", mode="DC", context=f"Seed evidence for {fault['name']}")]
    return await _seed_demo(
        topology=topology,
        title=f"{catalog.get('label', topology)}: {fault['name']}",
        notes=f"Seeded fault-gallery scenario for {fault_id}.",
        sample_dir=sample_dir,
        samples=samples[:6],
        measurements=measurements,
        question=f"I am trying the {fault['name']} scenario. What should I verify?",
    )


async def _seed_demo(
    topology: str,
    title: str,
    notes: str,
    sample_dir: Path,
    samples: list[tuple[str, str]],
    measurements: list[MeasurementCreate],
    question: str,
) -> dict:
    created = create_session(
        LabSessionCreate(
            title=title,
            student_level="2nd/3rd year EEE",
            notes=notes,
            experiment_type=topology,
        )
    )
    session_id = created["id"]
    for kind, filename in samples:
        path = sample_dir / filename
        if path.exists():
            _insert_artifact(session_id, kind, path, filename)

    for measurement in measurements:
        add_measurement(session_id, measurement)
    diagnosis = await diagnose_session(session_id, question)
    return {**get_session(session_id), "seed_diagnosis": diagnosis["diagnosis"]}


@app.post("/api/sessions/seed/rc-lowpass")
async def seed_rc_lowpass_demo() -> dict:
    return await _seed_demo(
        topology="rc_lowpass",
        title="RC Low-Pass: Why is 100 Hz already attenuated?",
        notes="Expected cutoff is about 159 Hz, but the observed output is too small at 100 Hz.",
        sample_dir=settings.sample_data_dir.parent / "rc_lowpass",
        samples=[
            ("manual", "lab_manual_excerpt.md"),
            ("netlist", "netlist.net"),
            ("waveform_csv", "expected_waveform.csv"),
            ("waveform_csv", "observed_attenuated.csv"),
            ("note", "student_question.txt"),
        ],
        measurements=[
            MeasurementCreate(label="output_gain_at_test_frequency", value=0.42, unit="ratio", mode="AC", context="100 Hz output/input gain"),
        ],
        question="The low-pass output is attenuated at 100 Hz. What should I check?",
    )


@app.post("/api/sessions/seed/voltage-divider")
async def seed_voltage_divider_demo() -> dict:
    return await _seed_demo(
        topology="voltage_divider",
        title="Voltage Divider: Why is the loaded output 1.8V?",
        notes="No-load expectation is 6 V from a 10k/10k divider on 12 V.",
        sample_dir=settings.sample_data_dir.parent / "voltage_divider",
        samples=[
            ("manual", "lab_manual_excerpt.md"),
            ("netlist", "netlist.net"),
            ("waveform_csv", "expected_waveform.csv"),
            ("waveform_csv", "observed_loaded.csv"),
            ("note", "student_question.txt"),
        ],
        measurements=[
            MeasurementCreate(label="loaded_vout", value=1.8, unit="V", mode="DC", context="Divider output with load connected"),
        ],
        question="My loaded divider output is 1.8 V instead of 6 V. What should I check?",
    )


@app.post("/api/sessions/seed/bjt-common-emitter")
async def seed_bjt_common_emitter_demo() -> dict:
    return await _seed_demo(
        topology="bjt_common_emitter",
        title="BJT Common Emitter: Why is the collector at 0.2V?",
        notes="The collector should bias near mid-supply, but it is near saturation.",
        sample_dir=settings.sample_data_dir.parent / "bjt_common_emitter",
        samples=[
            ("manual", "lab_manual_excerpt.md"),
            ("netlist", "netlist.net"),
            ("waveform_csv", "expected_waveform.csv"),
            ("waveform_csv", "observed_saturated.csv"),
            ("note", "student_question.txt"),
        ],
        measurements=[
            MeasurementCreate(label="collector_voltage", value=0.2, unit="V", mode="DC", context="Collector DC operating point"),
        ],
        question="The collector is at 0.2 V and the amplifier is clipped. What should I check?",
    )


@app.post("/api/sessions/seed/op-amp-noninverting")
async def seed_op_amp_noninverting_demo() -> dict:
    return await _seed_demo(
        topology="op_amp_noninverting",
        title="Op-Amp Non-Inverting: Why is the gain only 1?",
        notes="Expected gain is 11, but observed gain is unity.",
        sample_dir=settings.sample_data_dir.parent / "op_amp_noninverting",
        samples=[
            ("manual", "lab_manual_excerpt.md"),
            ("netlist", "netlist.net"),
            ("waveform_csv", "expected_waveform.csv"),
            ("waveform_csv", "observed_unity_gain.csv"),
            ("note", "student_question.txt"),
        ],
        measurements=[
            MeasurementCreate(label="closed_loop_gain", value=1.0, unit="ratio", mode="AC", context="Observed Vout/Vin"),
        ],
        question="My non-inverting op-amp gain is only 1 instead of 11. What should I check?",
    )


@app.post("/api/sessions/{session_id}/artifacts")
async def upload_artifact(
    session_id: str,
    file: Annotated[UploadFile, File()],
    kind: Annotated[str | None, Form()] = None,
) -> dict:
    _get_session_or_404(session_id)
    artifact_id = str(uuid.uuid4())
    filename = Path(file.filename or "upload.bin").name
    safe_dir = settings.upload_dir / session_id
    safe_dir.mkdir(parents=True, exist_ok=True)
    dest = safe_dir / f"{artifact_id}_{filename}"
    with dest.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    excerpt = read_text_excerpt(dest)
    now = utc_now()
    artifact_kind = _artifact_kind(filename, kind)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO artifacts (id, session_id, kind, filename, path, text_excerpt, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, session_id, artifact_kind, filename, str(dest), excerpt, "{}", now),
        )
        row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    return row_to_dict(row)


@app.post("/api/sessions/{session_id}/artifacts/netlist")
def create_netlist_artifact(session_id: str, payload: dict = Body(...)) -> dict:
    _get_session_or_404(session_id)
    netlist = str(payload.get("netlist", "")).strip()
    if not netlist:
        raise HTTPException(status_code=400, detail="netlist required")
    artifact_id = str(uuid.uuid4())
    safe_dir = settings.upload_dir / session_id
    safe_dir.mkdir(parents=True, exist_ok=True)
    dest = safe_dir / f"{artifact_id}_recognized.net"
    dest.write_text(netlist)
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO artifacts (id, session_id, kind, filename, path, text_excerpt, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, session_id, "netlist", "recognized.net", str(dest), netlist[:1200], json.dumps({"source": "schematic_to_netlist"}), now),
        )
        row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    return row_to_dict(row)


@app.get("/api/sessions/{session_id}/artifacts")
def list_artifacts(session_id: str) -> list[dict]:
    _get_session_or_404(session_id)
    with db() as conn:
        rows = conn.execute("SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    artifact = _get_artifact_or_404(artifact_id)
    return FileResponse(artifact["path"], filename=artifact["filename"])


@app.post("/api/sessions/{session_id}/measurements")
def add_measurement(session_id: str, payload: MeasurementCreate) -> dict:
    _get_session_or_404(session_id)
    measurement_id = str(uuid.uuid4())
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO measurements (id, session_id, label, value, unit, mode, context, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                measurement_id,
                session_id,
                payload.label,
                payload.value,
                payload.unit,
                payload.mode,
                payload.context,
                payload.source,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM measurements WHERE id = ?", (measurement_id,)).fetchone()
    return row_to_dict(row)


@app.get("/api/sessions/{session_id}/measurements")
def list_measurements(session_id: str) -> list[dict]:
    _get_session_or_404(session_id)
    with db() as conn:
        rows = conn.execute("SELECT * FROM measurements WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/sessions/{session_id}/bench/start")
def start_bench(session_id: str) -> dict:
    _get_session_or_404(session_id)
    with db() as conn:
        conn.execute("UPDATE lab_sessions SET status = ?, updated_at = ? WHERE id = ?", ("bench", utc_now(), session_id))
    return {"bench_url": f"{settings.frontend_origin}/bench/{session_id}"}


@app.get("/api/sessions/{session_id}/bench/qr")
def bench_qr(session_id: str) -> dict:
    _get_session_or_404(session_id)
    url = f"{settings.frontend_origin}/bench/{session_id}"
    image = qrcode.make(url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {"url": url, "data_url": f"data:image/png;base64,{encoded}"}


@app.post("/api/sessions/{session_id}/diagnose")
async def diagnose(session_id: str, payload: DiagnosisRequest | None = None) -> dict:
    _get_session_or_404(session_id)
    return await diagnose_session(session_id, payload.message if payload else None, lang=payload.lang if payload else "en")


@app.get("/api/sessions/{session_id}/diagnoses")
def list_diagnoses(session_id: str) -> list[dict]:
    _get_session_or_404(session_id)
    with db() as conn:
        rows = conn.execute("SELECT * FROM diagnoses WHERE session_id = ? ORDER BY created_at DESC", (session_id,)).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/sessions/{session_id}/chat")
async def chat(session_id: str, payload: ChatRequest) -> dict:
    _get_session_or_404(session_id)
    with db() as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, "user", payload.message, json.dumps({"mode": payload.mode}), utc_now()),
        )
    result = await diagnose_session(session_id, payload.message, lang=payload.lang)
    diagnosis = result["diagnosis"]
    reply = (
        f"{diagnosis.get('student_explanation')}\n\n"
        f"Next: {diagnosis.get('next_measurement', {}).get('instruction')}\n\n"
        f"Safety: {' '.join(diagnosis.get('safety', {}).get('warnings', []))}"
    )
    with db() as conn:
        trace_tool_calls = [
            {"tool_name": call.get("tool_name"), "status": call.get("status"), "output": call.get("output")}
            for call in result["tool_calls"]
        ]
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                session_id,
                "assistant",
                reply,
                json.dumps({"diagnosis_id": result["id"], "tool_calls": trace_tool_calls}),
                utc_now(),
            ),
        )
    return {
        "reply": reply,
        "diagnosis": diagnosis,
        "tool_calls": result["tool_calls"],
        "next_measurement": diagnosis.get("next_measurement"),
        "safety": diagnosis.get("safety"),
    }


@app.post("/api/sessions/{session_id}/report")
def generate_lab_report(session_id: str) -> dict:
    _get_session_or_404(session_id)
    return {"session_id": session_id, "markdown": build_report(session_id)}


@app.get("/api/sessions/{session_id}/report")
def get_lab_report(session_id: str) -> dict:
    _get_session_or_404(session_id)
    with db() as conn:
        report = row_to_dict(conn.execute("SELECT * FROM reports WHERE session_id = ?", (session_id,)).fetchone())
    if not report:
        return {"session_id": session_id, "markdown": ""}
    return {"session_id": session_id, "markdown": report["markdown"]}


@app.get("/api/sessions/{session_id}/report.pdf")
def get_lab_report_pdf(session_id: str) -> Response:
    session = _get_session_or_404(session_id)
    with db() as conn:
        measurements = rows_to_dicts(conn.execute("SELECT * FROM measurements WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall())
        artifacts = rows_to_dicts(conn.execute("SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall())
        diagnosis_row = conn.execute("SELECT * FROM diagnoses WHERE session_id = ? ORDER BY created_at DESC LIMIT 1", (session_id,)).fetchone()
    diagnosis = row_to_dict(diagnosis_row)
    diagnosis_json = diagnosis["diagnosis_json"] if diagnosis else None
    netlist_artifact = next((artifact for artifact in artifacts if artifact["kind"] == "netlist" and Path(artifact["path"]).exists()), None)
    parsed_netlist = parse_netlist_file(netlist_artifact["path"]) if netlist_artifact else None
    pdf = generate_report_pdf(session, diagnosis_json, measurements, parsed_netlist, artifacts)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{session_id}-circuitsage-report.pdf"'},
    )
