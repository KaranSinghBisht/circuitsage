from __future__ import annotations

import base64
import io
import json
import shutil
import uuid
from contextlib import asynccontextmanager
from collections import Counter
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Annotated

import qrcode
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import db, init_db, read_text_excerpt, row_to_dict, rows_to_dicts, utc_now
from .schemas import (
    ChatRequest,
    CompanionAnalyzeRequest,
    CompanionRunToolRequest,
    DiagnosisRequest,
    LabSessionCreate,
    LabSessionUpdate,
    MeasurementCreate,
    MeasurementStreamCreate,
)
from .services.agent_orchestrator import build_report, diagnose_session
from .services.companion_orchestrator import (
    SUPPORTED_TOPOLOGIES as COMPANION_SUPPORTED_TOPOLOGIES,
    analyze as companion_orchestrator_analyze,
)
from .services.fault_catalog import CATALOG, score as score_faults
from .services.ollama_client import OllamaClient, parse_json_response
from .tools.datasheet import datasheet_prompt_context
from .tools.rag import retrieve as retrieve_rag
from .services.streaming import add_sample as add_stream_sample
from .services.streaming import snapshot as stream_snapshot
from .tools.parse_netlist import parse_netlist_file
from .tools.report_builder import generate_report_pdf
from .tools.datasheet import lookup_datasheet
from .tools.safety_check import safety_check
from .tools.schematic_to_netlist import image_file_to_base64, recognize_schematic


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="CircuitSage API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
_hosted_rate_buckets: dict[str, deque[float]] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _hosted_allowed_write(path: str) -> bool:
    if path.startswith("/api/sessions/seed"):
        return True
    if path.startswith("/api/tools/schematic-to-netlist"):
        return True
    if not path.startswith("/api/sessions/"):
        return False
    return path.endswith(("/diagnose", "/measurements", "/measurements/stream", "/chat", "/report"))


def _hosted_client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def _hosted_rate_limited(request: Request) -> bool:
    limit = max(settings.hosted_rate_limit_per_minute, 1)
    key = _hosted_client_key(request)
    now = monotonic()
    bucket = _hosted_rate_buckets.setdefault(key, deque())
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


@app.middleware("http")
async def hosted_demo_guard(request: Request, call_next):
    if not settings.hosted_demo:
        return await call_next(request)
    path = request.url.path
    if path.startswith("/api/companion") or "/bench" in path:
        return JSONResponse(
            {"detail": "Companion and Bench Mode need local LAN/native permissions and are disabled on the public hosted demo."},
            status_code=403,
        )
    if path.startswith("/api/") and request.method in {"POST", "PATCH", "DELETE"}:
        if request.method in {"PATCH", "DELETE"} or not _hosted_allowed_write(path):
            return JSONResponse({"detail": "Public hosted demo is read-only except seeded demo actions."}, status_code=403)
        if _hosted_rate_limited(request):
            return JSONResponse({"detail": "Hosted demo rate limit exceeded. Try again in a minute."}, status_code=429)
    return await call_next(request)


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


def _guess_workspace(app_hint: str, question: str, source_title: str = "") -> str:
    text = f"{app_hint} {source_title} {question}".lower()
    if "tinkercad" in text or "arduino" in text or "breadboard" in text or "bulb" in text or "led" in text:
        return "tinkercad"
    if "ltspice" in text or "spice" in text or ".tran" in text or ".op" in text or ".asc" in text:
        return "ltspice"
    if "matlab" in text or "simulink" in text or "plot" in text or ".m" in text:
        return "matlab"
    return "electronics_workspace"


COMPANION_SESSION_REUSE_WINDOW_S = 4 * 60 * 60  # 4 hours
COMPANION_RECENT_TURNS = 3


def _companion_session_title(workspace: str) -> str:
    label = {
        "ltspice": "LTspice",
        "tinkercad": "Tinkercad",
        "matlab": "MATLAB",
        "simulink": "Simulink",
        "oscilloscope": "Oscilloscope",
        "browser_lab": "Browser lab",
        "electronics_workspace": "Electronics workspace",
    }.get(workspace, workspace.replace("_", " ").title())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"Companion · {label} · {today}"


def _resolve_or_create_companion_session(
    requested_id: str | None, workspace: str
) -> dict:
    """Return an existing companion session if recent and matching, else create a new one.

    Lets the LTspice→ask→ask→ask flow accumulate evidence in one session without
    requiring the desktop overlay to manage state. A new session opens per workspace
    after a 4-hour quiet period.
    """
    now_iso = utc_now()
    with db() as conn:
        if requested_id:
            row = conn.execute("SELECT * FROM lab_sessions WHERE id = ?", (requested_id,)).fetchone()
            if row:
                return row_to_dict(row) or {}

        recent = conn.execute(
            """
            SELECT * FROM lab_sessions
            WHERE experiment_type = ?
              AND title LIKE 'Companion %'
              AND updated_at >= datetime('now', ?)
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (f"companion_{workspace}", f"-{COMPANION_SESSION_REUSE_WINDOW_S} seconds"),
        ).fetchone()
        if recent:
            return row_to_dict(recent) or {}

        session_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO lab_sessions (id, title, student_level, experiment_type, status, created_at, updated_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                _companion_session_title(workspace),
                "companion",
                f"companion_{workspace}",
                "bench",
                now_iso,
                now_iso,
                "Auto-created from CircuitSage Companion screen capture.",
            ),
        )
        row = conn.execute("SELECT * FROM lab_sessions WHERE id = ?", (session_id,)).fetchone()
    return row_to_dict(row) or {}


def _save_companion_message(session_id: str, role: str, content: str, metadata: dict | None = None) -> None:
    if not content:
        return
    with db() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, session_id, role, content, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                role,
                content,
                json.dumps({"source": "companion", **(metadata or {})}),
                utc_now(),
            ),
        )
        conn.execute(
            "UPDATE lab_sessions SET updated_at = ? WHERE id = ?",
            (utc_now(), session_id),
        )


def _load_companion_recent_turns(session_id: str, limit: int = COMPANION_RECENT_TURNS) -> list[dict]:
    """Return last N (user, assistant) message pairs for the given companion session."""
    with db() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at FROM messages
            WHERE session_id = ? AND role IN ('user', 'assistant')
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit * 2),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


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


@app.get("/api/routes")
def api_routes() -> list[dict]:
    routes: list[dict] = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        methods = sorted(method for method in route.methods if method not in {"HEAD", "OPTIONS"})
        description = route.summary or route.name.replace("_", " ")
        for method in methods:
            routes.append(
                {
                    "method": method,
                    "path": route.path,
                    "description": " ".join(description.split()),
                }
            )
    return sorted(routes, key=lambda item: (item["path"], item["method"]))


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
    """Companion entry. Safety-first ordering: refuse and short-circuit BEFORE
    persisting anything dangerous; gate disk writes on `save_snapshot`; load
    prior turns BEFORE saving the current user message so the new question
    doesn't echo back into its own prompt.
    """
    image_bytes = _decode_data_url(payload.image_data_url)
    image_base64 = _image_base64_from_data_url(payload.image_data_url)
    workspace = _guess_workspace(payload.app_hint, payload.question, payload.source_title)

    # Safety screen before we touch the database. A high-voltage question
    # never gets persisted as a user message and never creates a session.
    pre_safety = safety_check(payload.question or "")
    if not pre_safety["allowed"]:
        return await companion_orchestrator_analyze(
            question=payload.question,
            image_base64=None,  # do not relay the image either
            workspace=workspace,
            app_hint=payload.app_hint,
            source_title=payload.source_title,
            lang=payload.lang,
            settings=settings,
            saved_artifact=None,
            prior_turns=[],
        )

    session = _resolve_or_create_companion_session(payload.session_id, workspace)
    session_id = session["id"]

    # Load prior context BEFORE we persist the new question so the prompt
    # gets {prior turns ... + current question} not {... + current question
    # echoed back as the most recent prior turn}.
    prior_turns = _load_companion_recent_turns(session_id)

    saved_artifact = None
    if image_bytes and payload.save_snapshot:
        saved_artifact = _save_companion_snapshot(session_id, image_bytes)

    if payload.question:
        _save_companion_message(
            session_id,
            "user",
            payload.question,
            {"workspace": workspace, "source_title": payload.source_title or ""},
        )

    response = await companion_orchestrator_analyze(
        question=payload.question,
        image_base64=image_base64,
        workspace=workspace,
        app_hint=payload.app_hint,
        source_title=payload.source_title,
        lang=payload.lang,
        settings=settings,
        saved_artifact=saved_artifact,
        prior_turns=prior_turns,
    )

    response["session_id"] = session_id
    response["session_title"] = session.get("title", "")
    response["turn_count"] = len(prior_turns) // 2 + 1

    assistant_text = response.get("user_facing_answer") or response.get("answer", "")
    if assistant_text:
        _save_companion_message(
            session_id,
            "assistant",
            assistant_text,
            {
                "mode": response.get("mode"),
                "detected_topology": response.get("detected_topology"),
                "confidence": response.get("confidence"),
            },
        )

    return response


@app.post("/api/companion/run-tool")
async def companion_run_tool(payload: CompanionRunToolRequest) -> dict:
    """Click-to-act endpoint for the companion overlay's typed actions (P3).

    The overlay surfaces deterministic tools as buttons. Clicking one POSTs here.
    Result is returned inline and (if session_id provided) saved as a tool message.
    """
    import time as _time
    started = _time.perf_counter()
    tool = payload.tool
    args = payload.args or {}

    if tool == "score_faults":
        topology = str(args.get("topology", "")).strip()
        if topology not in COMPANION_SUPPORTED_TOPOLOGIES:
            raise HTTPException(status_code=400, detail=f"unsupported topology: {topology}")
        ranked = score_faults(topology, {"likely_fault_categories": []}, [])
        result = {"topology": topology, "ranked_faults": ranked[:5]}
    elif tool == "lookup_datasheet":
        part_number = str(args.get("part_number", "")).strip()
        if not part_number:
            raise HTTPException(status_code=400, detail="part_number is required")
        raw = lookup_datasheet(part_number)
        result = datasheet_prompt_context(raw)
    elif tool == "retrieve_rag":
        query = str(args.get("query", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        topology = args.get("topology")
        topology_filter = topology if topology in COMPANION_SUPPORTED_TOPOLOGIES else None
        result = retrieve_rag(query, topology=topology_filter, k=3)
    else:  # pragma: no cover - guarded by Literal in schema
        raise HTTPException(status_code=400, detail=f"unknown tool: {tool}")

    duration_ms = round((_time.perf_counter() - started) * 1000)

    if payload.session_id:
        try:
            _get_session_or_404(payload.session_id)
            _save_companion_message(
                payload.session_id,
                "assistant",
                f"Ran tool `{tool}` ({duration_ms} ms).",
                {"tool_name": tool, "args": args, "duration_ms": duration_ms},
            )
        except HTTPException:
            pass  # session not found is non-fatal for the click-to-act flow

    return {"tool": tool, "args": args, "result": result, "duration_ms": duration_ms}


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


@app.get("/api/datasheets/{partnumber}")
def get_datasheet(partnumber: str) -> dict:
    return lookup_datasheet(partnumber)


@app.get("/api/educator/overview")
def educator_overview() -> dict:
    with db() as conn:
        sessions = rows_to_dicts(conn.execute("SELECT * FROM lab_sessions").fetchall())
        diagnoses = rows_to_dicts(conn.execute("SELECT * FROM diagnoses").fetchall())
    common: Counter[tuple[str, str]] = Counter()
    stalled: Counter[str] = Counter()
    safety_refusals = 0
    resolved_durations: list[float] = []
    session_by_id = {session["id"]: session for session in sessions}
    for row in diagnoses:
        diagnosis = row.get("diagnosis_json", {})
        topology = diagnosis.get("experiment_type", "unknown")
        top_fault = (diagnosis.get("likely_faults") or [{}])[0]
        fault = top_fault.get("id") or top_fault.get("fault") or top_fault.get("name")
        if fault:
            common[(topology, fault)] += 1
        next_label = diagnosis.get("next_measurement", {}).get("label")
        if next_label:
            stalled[next_label] += 1
        if diagnosis.get("gemma_status") == "blocked_by_safety" or diagnosis.get("safety", {}).get("risk_level") == "high_voltage_or_mains":
            safety_refusals += 1
        session = session_by_id.get(row["session_id"])
        if session and session.get("status") == "resolved":
            try:
                resolved_durations.append((datetime.fromisoformat(session["updated_at"]) - datetime.fromisoformat(session["created_at"])).total_seconds())
            except (TypeError, ValueError):
                pass
    return {
        "total_sessions": len(sessions),
        "average_time_to_resolution_s": round(sum(resolved_durations) / len(resolved_durations), 2) if resolved_durations else None,
        "safety_refusals": safety_refusals,
        "unfinished_sessions": sum(1 for session in sessions if session.get("status") not in {"resolved", "archived"}),
        "common_faults": [
            {"topology": topology, "fault": fault, "count": count}
            for (topology, fault), count in common.most_common(12)
        ],
        "stalled_measurements": [
            {"label": label, "count": count}
            for label, count in stalled.most_common(12)
        ],
    }


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


SEED_TO_TOPOLOGY = {
    "full-wave-rectifier": "full_wave_rectifier",
    "active-highpass": "active_highpass_filter",
    "integrator": "op_amp_integrator",
    "differentiator": "op_amp_differentiator",
    "schmitt-trigger": "schmitt_trigger",
    "timer-555-astable": "timer_555_astable",
    "nmos-low-side": "nmos_low_side_switch",
    "instrumentation-amplifier": "instrumentation_amplifier",
}


@app.post("/api/sessions/seed/{slug}")
async def seed_topology_demo(slug: str) -> dict:
    topology = SEED_TO_TOPOLOGY.get(slug)
    if not topology:
        raise HTTPException(status_code=404, detail="Seed not found")
    catalog = CATALOG.get(topology, {"label": topology.replace("_", " "), "faults": []})
    first_fault = (catalog.get("faults") or [{"name": "starter evidence", "requires_measurements": ["observed_node"]}])[0]
    sample_dir = settings.sample_data_dir.parent / topology
    samples = []
    for filename in ("lab_manual_excerpt.md", "netlist.net", "expected_waveform.csv", "observed_fault.csv", "student_question.txt"):
        if (sample_dir / filename).exists():
            samples.append((_artifact_kind(filename), filename))
    measurement = MeasurementCreate(
        label=(first_fault.get("requires_measurements") or ["observed_node"])[0],
        value=1.0,
        unit="V",
        mode="DC",
        context=f"Seed measurement for {first_fault.get('name')}",
    )
    return await _seed_demo(
        topology=topology,
        title=f"{catalog.get('label', topology)} demo",
        notes=f"Seeded topology-pack scenario for {topology}.",
        sample_dir=sample_dir,
        samples=samples,
        measurements=[measurement],
        question=f"My {catalog.get('label', topology)} is not matching the expected behavior. What should I check?",
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


@app.post("/api/sessions/{session_id}/measurements/stream")
def stream_measurement(session_id: str, payload: MeasurementStreamCreate) -> dict:
    _get_session_or_404(session_id)
    return add_stream_sample(session_id, payload.label, payload.value, payload.unit, payload.ts)


@app.get("/api/sessions/{session_id}/measurements/stream")
def get_stream_measurements(session_id: str) -> dict:
    _get_session_or_404(session_id)
    return stream_snapshot(session_id)


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


if settings.frontend_dist_dir.exists():
    app.mount("/", StaticFiles(directory=settings.frontend_dist_dir, html=True), name="frontend")
