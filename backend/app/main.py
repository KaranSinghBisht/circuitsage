from __future__ import annotations

import base64
import io
import json
import shutil
import uuid
from pathlib import Path
from typing import Annotated

import qrcode
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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
from .services.ollama_client import OllamaClient, parse_json_response
from .tools.safety_check import safety_check


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
        return "image"
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
- Refuse detailed live debugging for mains/high-voltage.
"""
    if not image_base64:
        return {**fallback, "saved_artifact": saved_artifact}

    try:
        result = await OllamaClient(settings.ollama_base_url, settings.ollama_model).chat(
            [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64],
                }
            ],
            format_json=True,
        )
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
                "op_amp_inverting",
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
    created = create_session(
        LabSessionCreate(
            title="Op-Amp Inverting Amplifier: Why is my output stuck at +12V?",
            student_level="2nd/3rd year EEE",
            notes="Seeded hackathon demo: simulation is correct, bench output is saturated near +12 V.",
        )
    )
    session_id = created["id"]
    samples = [
        ("manual", "lab_manual_excerpt.md"),
        ("netlist", "opamp_inverting.net"),
        ("waveform_csv", "expected_waveform.csv"),
        ("waveform_csv", "observed_saturated_waveform.csv"),
        ("note", "student_question.txt"),
        ("image", "scope_saturated_placeholder.png"),
        ("image", "breadboard_placeholder.png"),
        ("image", "fixed_scope_placeholder.png"),
    ]
    for kind, filename in samples:
        path = settings.sample_data_dir / filename
        if path.exists():
            _insert_artifact(session_id, kind, path, filename)

    seed_measurements = [
        MeasurementCreate(label="Vout", value=11.8, unit="V", mode="DC", context="Output stuck near positive rail"),
        MeasurementCreate(label="V+", value=12.1, unit="V", mode="DC", context="Positive supply rail"),
        MeasurementCreate(label="V-", value=-12.0, unit="V", mode="DC", context="Negative supply rail"),
    ]
    for measurement in seed_measurements:
        add_measurement(session_id, measurement)
    diagnosis = await diagnose_session(session_id, "My output is stuck near +12V. What should I check first?")
    return {**get_session(session_id), "seed_diagnosis": diagnosis["diagnosis"]}


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


@app.get("/api/sessions/{session_id}/artifacts")
def list_artifacts(session_id: str) -> list[dict]:
    _get_session_or_404(session_id)
    with db() as conn:
        rows = conn.execute("SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    with db() as conn:
        artifact = row_to_dict(conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone())
    if not artifact or not Path(artifact["path"]).exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
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
    return await diagnose_session(session_id, payload.message if payload else None)


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
    result = await diagnose_session(session_id, payload.message)
    diagnosis = result["diagnosis"]
    reply = (
        f"{diagnosis.get('student_explanation')}\n\n"
        f"Next: {diagnosis.get('next_measurement', {}).get('instruction')}\n\n"
        f"Safety: {' '.join(diagnosis.get('safety', {}).get('warnings', []))}"
    )
    with db() as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, "assistant", reply, json.dumps({"diagnosis_id": result["id"]}), utc_now()),
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
