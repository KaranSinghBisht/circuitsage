from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..database import db, row_to_dict, rows_to_dicts, utc_now
from ..tools.measurement_compare import compare_expected_vs_observed
from ..tools.parse_netlist import parse_netlist_file
from ..tools.rag import retrieve_lab_manual
from ..tools.report_builder import generate_report
from ..tools.safety_check import safety_check
from ..tools.waveform_analysis import analyze_waveform_csv
from .ollama_client import OllamaClient, parse_json_response
from .prompt_templates import STRUCTURED_DIAGNOSIS_PROMPT, SYSTEM_PROMPT


def _load_session_context(session_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    with db() as conn:
        session = row_to_dict(conn.execute("SELECT * FROM lab_sessions WHERE id = ?", (session_id,)).fetchone())
        artifacts = rows_to_dicts(conn.execute("SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall())
        measurements = rows_to_dicts(
            conn.execute("SELECT * FROM measurements WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall()
        )
    if not session:
        raise ValueError("session_not_found")
    return session, artifacts, measurements


def _tool_call(name: str, started: float, output: dict[str, Any], status: str = "ok") -> dict[str, Any]:
    return {
        "tool_name": name,
        "input": {},
        "output": output,
        "status": status,
        "duration_ms": round((time.perf_counter() - started) * 1000),
    }


def _artifact_path(artifact: dict[str, Any]) -> Path:
    return Path(artifact["path"])


def _find_artifact(artifacts: list[dict[str, Any]], kind: str, contains: str | None = None) -> dict[str, Any] | None:
    candidates = [artifact for artifact in artifacts if artifact["kind"] == kind]
    if contains:
        lowered = contains.lower()
        exact = [artifact for artifact in candidates if lowered in artifact["filename"].lower()]
        if exact:
            return exact[-1]
    return candidates[-1] if candidates else None


def _fallback_diagnosis(
    session: dict[str, Any],
    netlist: dict[str, Any],
    waveform: dict[str, Any],
    comparison: dict[str, Any],
    measurements: list[dict[str, Any]],
    safety: dict[str, Any],
) -> dict[str, Any]:
    expected_gain = netlist.get("computed", {}).get("gain", -4.7)
    labels = {m["label"].lower(): m for m in measurements}
    noninv = next((m for key, m in labels.items() if "non" in key or "v_noninv" in key or "pin 3" in key), None)

    likely_faults = [
        {
            "fault": "Floating or incorrectly biased non-inverting input",
            "confidence": 0.86 if noninv and abs(float(noninv["value"])) > 0.5 else 0.78,
            "why": "A floating reference input can drive the op-amp into saturation even when the feedback network is correct.",
        },
        {
            "fault": "Feedback path disconnected or wired to wrong node",
            "confidence": 0.55,
            "why": "Without negative feedback, an op-amp can saturate at a rail.",
        },
        {
            "fault": "Power rail or common ground issue",
            "confidence": 0.35,
            "why": "The rails look plausible, but a missing common reference can still create misleading behavior.",
        },
    ]

    next_measurement = {
        "label": "Voltage at non-inverting input pin",
        "expected": "approximately 0 V",
        "instruction": "Measure the non-inverting input with respect to circuit ground before changing resistor values.",
    }
    explanation = (
        "The simulation expects gain around -4.7, but the observed output is saturated near the positive rail. "
        "Since both supply rails look correct, the next best measurement is the non-inverting input voltage."
    )
    status = "diagnosing"
    confidence = "medium_high"

    if noninv and abs(float(noninv["value"])) > 0.5:
        next_measurement = {
            "label": "Retest Vout after grounding non-inverting input",
            "expected": "inverted sine wave near 4.7 V peak",
            "instruction": "Power off, tie the non-inverting input to circuit ground, power on, and retest the output waveform.",
        }
        explanation = (
            "That measurement confirms the likely issue: the non-inverting input is not at the 0 V reference. "
            "This is a reference/feedback problem, not a gain-formula problem."
        )
        status = "resolved"
        confidence = "high"

    return {
        "experiment_type": session.get("experiment_type", "op_amp_inverting"),
        "expected_behavior": {
            "gain": expected_gain,
            "output": f"inverted sine wave, about {abs(expected_gain)} V peak for 1 V peak input",
        },
        "observed_behavior": {
            "summary": "Output is stuck near the positive supply rail"
            if waveform.get("is_saturated")
            else "More bench evidence is needed",
            "evidence": [
                *(f"{m['label']} = {m['value']} {m['unit']} {m['mode']}" for m in measurements),
                f"waveform analysis: {comparison.get('mismatch_type')}",
            ],
        },
        "likely_faults": likely_faults,
        "next_measurement": next_measurement,
        "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
        "student_explanation": explanation,
        "confidence": confidence,
        "session_status": status,
    }


async def diagnose_session(session_id: str, user_message: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    session, artifacts, measurements = _load_session_context(session_id)
    user_message = user_message or ""
    combined_text = " ".join([user_message, session.get("summary", ""), *[a.get("text_excerpt", "") for a in artifacts]])

    tool_calls: list[dict[str, Any]] = []
    started = time.perf_counter()
    safety = safety_check(combined_text)
    tool_calls.append(_tool_call("safety_check", started, safety))
    if not safety["allowed"]:
        diagnosis = {
            "experiment_type": session.get("experiment_type", "unknown"),
            "expected_behavior": {},
            "observed_behavior": {"summary": "High-voltage or mains risk was detected.", "evidence": [user_message]},
            "likely_faults": [],
            "next_measurement": {
                "label": "Stop live debugging",
                "expected": "qualified supervision",
                "instruction": safety["message"],
            },
            "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
            "student_explanation": safety["message"],
            "confidence": "high",
        }
        return _save_diagnosis(session_id, diagnosis, tool_calls, gemma_status="blocked_by_safety")

    netlist: dict[str, Any] = {"components": [], "detected_topology": "op_amp_inverting", "computed": {"gain": -4.7}}
    netlist_artifact = _find_artifact(artifacts, "netlist")
    if netlist_artifact:
        started = time.perf_counter()
        netlist = parse_netlist_file(_artifact_path(netlist_artifact))
        tool_calls.append(_tool_call("parse_netlist", started, netlist))

    waveform: dict[str, Any] = {}
    waveform_artifact = _find_artifact(artifacts, "waveform_csv", "observed") or _find_artifact(artifacts, "waveform_csv")
    if waveform_artifact:
        started = time.perf_counter()
        waveform = analyze_waveform_csv(_artifact_path(waveform_artifact))
        tool_calls.append(_tool_call("analyze_waveform_csv", started, waveform))

    manual_artifact = _find_artifact(artifacts, "manual")
    manual = {"snippets": []}
    if manual_artifact:
        started = time.perf_counter()
        manual = retrieve_lab_manual(_artifact_path(manual_artifact), user_message or "saturation non-inverting ground")
        tool_calls.append(_tool_call("retrieve_lab_manual", started, manual))

    started = time.perf_counter()
    comparison = compare_expected_vs_observed(netlist.get("computed", {}).get("gain"), waveform, measurements)
    tool_calls.append(_tool_call("compare_expected_vs_observed", started, comparison))

    fallback = _fallback_diagnosis(session, netlist, waveform, comparison, measurements, safety)
    context = {
        "session": session,
        "measurements": measurements,
        "netlist": netlist,
        "waveform": waveform,
        "manual": manual,
        "comparison": comparison,
        "deterministic_diagnosis": fallback,
        "student_message": user_message,
    }

    gemma_status = "deterministic_fallback"
    diagnosis = fallback
    try:
        client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        content = await client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": STRUCTURED_DIAGNOSIS_PROMPT.format(context=json.dumps(context, indent=2))},
            ],
            format_json=True,
        )
        parsed = parse_json_response(content)
        if parsed:
            diagnosis = {**fallback, **parsed}
            gemma_status = "ollama_gemma"
    except Exception as exc:  # noqa: BLE001 - fallback is the required demo behavior.
        gemma_status = f"deterministic_fallback: {exc.__class__.__name__}"

    return _save_diagnosis(session_id, diagnosis, tool_calls, gemma_status=gemma_status)


def _save_diagnosis(
    session_id: str,
    diagnosis: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    gemma_status: str,
) -> dict[str, Any]:
    diagnosis = {**diagnosis, "tool_calls": tool_calls, "gemma_status": gemma_status}
    diagnosis_id = str(uuid.uuid4())
    now = utc_now()
    with db() as conn:
        conn.execute(
            "INSERT INTO diagnoses (id, session_id, diagnosis_json, created_at) VALUES (?, ?, ?, ?)",
            (diagnosis_id, session_id, json.dumps(diagnosis), now),
        )
        conn.execute(
            "UPDATE lab_sessions SET status = ?, updated_at = ? WHERE id = ?",
            (diagnosis.get("session_status", "diagnosing"), now, session_id),
        )
    return {"id": diagnosis_id, "session_id": session_id, "diagnosis": diagnosis, "tool_calls": tool_calls}


def build_report(session_id: str) -> str:
    session, _, measurements = _load_session_context(session_id)
    with db() as conn:
        diagnosis_row = conn.execute(
            "SELECT * FROM diagnoses WHERE session_id = ? ORDER BY created_at DESC LIMIT 1", (session_id,)
        ).fetchone()
    diagnosis = row_to_dict(diagnosis_row)
    diagnosis_json = diagnosis["diagnosis_json"] if diagnosis else None
    markdown = generate_report(session, diagnosis_json, measurements)
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO reports (session_id, markdown, updated_at) VALUES (?, ?, ?)",
            (session_id, markdown, utc_now()),
        )
    return markdown

