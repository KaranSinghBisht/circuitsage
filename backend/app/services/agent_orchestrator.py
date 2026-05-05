from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..database import db, row_to_dict, rows_to_dicts, utc_now
from ..tools.measurement_compare import compare_expected_vs_observed
from ..tools.parse_netlist import parse_netlist_file
from ..tools.rag import retrieve
from ..tools.report_builder import generate_report
from ..tools.safety_check import safety_check
from ..tools.schematic_to_netlist import image_file_to_base64, recognize_schematic
from ..tools.vision import describe_artifact
from ..tools.waveform_analysis import analyze_waveform_csv
from .fault_catalog import build_catalog_diagnosis
from .ollama_client import OllamaClient, parse_json_response
from .prompt_templates import AGENTIC_SYSTEM_PROMPT, STRUCTURED_DIAGNOSIS_PROMPT
from .tool_runner import AgentContext, run_tool


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "compute_expected_value",
            "description": "Compute an expected circuit value from parsed topology data.",
            "parameters": {"type": "object", "properties": {"quantity": {"type": "string"}}, "required": ["quantity"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_measurement",
            "description": "Ask the student for one concrete next bench measurement.",
            "parameters": {"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_image",
            "description": "Ask for a photo or screenshot of a specific circuit area.",
            "parameters": {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cite_textbook",
            "description": "Cite a relevant manual or textbook snippet already retrieved.",
            "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_with_simulation",
            "description": "Describe a simulation check that would verify the suspected fault.",
            "parameters": {"type": "object", "properties": {"check": {"type": "string"}}, "required": ["check"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": "Return the final structured diagnosis JSON and end the agent loop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "experiment_type": {"type": "string"},
                    "expected_behavior": {"type": "object"},
                    "observed_behavior": {"type": "object"},
                    "likely_faults": {"type": "array", "items": {"type": "object"}},
                    "next_measurement": {"type": "object"},
                    "safety": {"type": "object"},
                    "student_explanation": {"type": "string"},
                    "confidence": {"type": "string"},
                },
                "required": [
                    "experiment_type",
                    "expected_behavior",
                    "observed_behavior",
                    "likely_faults",
                    "next_measurement",
                    "safety",
                    "student_explanation",
                    "confidence",
                ],
            },
        },
    },
]


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


def _load_recent_messages(session_id: str, limit: int = 8) -> list[dict[str, str]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM messages
            WHERE session_id = ? AND role IN ('user', 'assistant')
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def _measurements_from_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    uncertainty = re.compile(r"\b(expected|should be|predicted|in theory|the lab manual says)\b", re.IGNORECASE)
    measurement_context = (
        r"(?:i\s+(?:measured|got|read|saw|see)|measured(?:\s+a)?|reading\s+(?:was|is|of)|"
        r"the\s+meter\s+(?:shows|read|reads)|i\s+have\s+about|comes\s+out\s+to|came\s+out\s+to|got)"
    )
    value_after_context = re.compile(
        measurement_context + r"[^0-9+-]{0,20}([+-]?\d+(?:\.\d+)?)\s*(V|volts?)?",
        re.IGNORECASE,
    )
    labels = [
        (re.compile(r"\b(V[_\s-]?noninv|non[-\s]?inverting(?: input)?|pin 3)\b", re.IGNORECASE), "V_noninv"),
        (re.compile(r"\b(V\+|positive rail)\b", re.IGNORECASE), "V+"),
        (re.compile(r"\b(V-|negative rail)\b", re.IGNORECASE), "V-"),
        (re.compile(r"\b(Vc|collector(?: voltage)?)\b", re.IGNORECASE), "collector_voltage"),
        (re.compile(r"\bloaded[_\s-]?vout\b", re.IGNORECASE), "loaded_vout"),
        (re.compile(r"\bVout\b", re.IGNORECASE), "Vout"),
    ]
    for message in messages:
        if message["role"] != "user":
            continue
        content = message["content"]
        if uncertainty.search(content):
            continue
        value_match = value_after_context.search(content)
        if not value_match:
            continue
        for label_pattern, label in labels:
            label_match = label_pattern.search(content)
            if label_match and abs(label_match.start() - value_match.start()) <= 100:
                extracted.append(
                    {
                        "id": f"memory_{len(extracted)}",
                        "label": label,
                        "value": float(value_match.group(1)),
                        "unit": "V",
                        "mode": "chat_memory",
                        "context": "extracted from recent chat",
                        "source": "chat_memory_inferred",
                        "metadata": {"source": "chat_memory_inferred", "confidence": "low"},
                    }
                )
    return extracted


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


def _tool_name_and_args(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    function = raw.get("function", {})
    name = function.get("name") or raw.get("name") or "unknown_tool"
    arguments = function.get("arguments", raw.get("arguments", {}))
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {"raw": arguments}
    if not isinstance(arguments, dict):
        arguments = {}
    return name, arguments


async def _agentic_loop(
    client: OllamaClient,
    system_prompt: str,
    user_prompt: str,
    history: list[dict[str, str]],
    tool_schemas: list[dict[str, Any]],
    context: AgentContext,
    max_iterations: int = 4,
    wall_clock_budget_s: float = 30.0,
) -> dict[str, Any]:
    transcript: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": user_prompt}]
    recorded_calls: list[dict[str, Any]] = []
    loop_started = time.monotonic()
    for index in range(max_iterations):
        if time.monotonic() - loop_started > wall_clock_budget_s:
            break
        chat = await client.chat(transcript, tools=tool_schemas, format_json=False)
        raw_tool_calls = chat.get("tool_calls", [])
        if not raw_tool_calls:
            return {"content": chat["content"], "tool_calls": recorded_calls, "iterations": index + 1}
        transcript.append({"role": "assistant", "content": chat.get("content", ""), "tool_calls": raw_tool_calls})
        for raw in raw_tool_calls[:3]:
            name, arguments = _tool_name_and_args(raw)
            started = time.perf_counter()
            if name == "final_answer":
                recorded_calls.append(
                    {
                        "tool_name": name,
                        "input": arguments,
                        "output": {"accepted": True},
                        "status": "ok",
                        "duration_ms": round((time.perf_counter() - started) * 1000),
                    }
                )
                return {"content": json.dumps(arguments), "tool_calls": recorded_calls, "iterations": index + 1}
            try:
                output = await run_tool(name, arguments, context=context)
                status = "ok"
            except Exception as exc:  # noqa: BLE001 - the model should see recoverable tool errors.
                output = {"error": str(exc), "tool": name}
                status = "error"
            transcript.append({"role": "tool", "name": name, "content": json.dumps(output)})
            recorded_calls.append(
                {
                    "tool_name": name,
                    "input": arguments,
                    "output": output,
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                }
            )
    transcript.append({"role": "user", "content": "Call final_answer now with the structured diagnosis JSON."})
    final = await client.chat(transcript, format_json=True)
    return {"content": final["content"], "tool_calls": recorded_calls, "iterations": max_iterations}


async def diagnose_session(session_id: str, user_message: str | None = None, lang: str = "en") -> dict[str, Any]:
    settings = get_settings()
    session, artifacts, measurements = _load_session_context(session_id)
    recent_messages = _load_recent_messages(session_id)
    memory_measurements = _measurements_from_messages(recent_messages)
    evidence_measurements = [*measurements, *memory_measurements]
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
        return _save_diagnosis(
            session_id,
            diagnosis,
            tool_calls,
            gemma_status="blocked_by_safety",
            gemma_model=settings.ollama_model,
        )

    netlist: dict[str, Any] = {"components": [], "detected_topology": "unknown", "computed": {}}
    netlist_artifact = _find_artifact(artifacts, "netlist")
    if netlist_artifact:
        started = time.perf_counter()
        netlist = parse_netlist_file(_artifact_path(netlist_artifact))
        tool_calls.append(_tool_call("parse_netlist", started, netlist))
    else:
        schematic_artifact = next(
            (
                artifact
                for artifact in reversed(artifacts)
                if artifact["kind"] in {"image", "breadboard"} and "schematic" in artifact.get("filename", "").lower()
            ),
            None,
        )
        if schematic_artifact:
            started = time.perf_counter()
            recognized = await recognize_schematic(
                image_file_to_base64(_artifact_path(schematic_artifact)),
                hint=schematic_artifact.get("filename", ""),
            )
            status = "ok" if recognized.get("detected_topology") != "unknown" else "fallback"
            tool_calls.append(_tool_call("schematic_to_netlist", started, recognized, status=status))
            if recognized.get("detected_topology") != "unknown":
                netlist = recognized.get("parsed", netlist)

    waveform: dict[str, Any] = {}
    waveform_artifact = _find_artifact(artifacts, "waveform_csv", "observed") or _find_artifact(artifacts, "waveform_csv")
    if waveform_artifact:
        started = time.perf_counter()
        waveform = analyze_waveform_csv(_artifact_path(waveform_artifact))
        tool_calls.append(_tool_call("analyze_waveform_csv", started, waveform))

    manual = {"snippets": []}
    manual_artifacts = [artifact for artifact in artifacts if artifact["kind"] == "manual"]

    started = time.perf_counter()
    comparison = compare_expected_vs_observed(netlist.get("computed", {}).get("gain"), waveform, evidence_measurements)
    tool_calls.append(_tool_call("compare_expected_vs_observed", started, comparison))

    fallback = build_catalog_diagnosis(session, netlist, waveform, comparison, evidence_measurements, safety)
    vision_results: list[dict[str, Any]] = []
    vision_artifacts = [artifact for artifact in artifacts if artifact["kind"] in {"breadboard", "oscilloscope"}]
    for artifact in list(reversed(vision_artifacts))[:2]:
        started = time.perf_counter()
        vision_result = await describe_artifact(artifact, settings.ollama_base_url, settings.ollama_vision_model)
        vision_results.append(vision_result)
        status = "ok" if vision_result.get("mode") == "ollama_gemma_vision" else "fallback"
        tool_calls.append(_tool_call("describe_artifact", started, vision_result, status=status))
    started = time.perf_counter()
    top_fault = (fallback.get("likely_faults") or [{}])[0]
    retrieve_query = " ".join(
        str(part)
        for part in [top_fault.get("id"), top_fault.get("name"), user_message or "circuit fault"]
        if part
    )
    if fallback.get("experiment_type") == "unknown":
        manual = {"snippets": [], "from_corpus": 0, "from_session": 0}
    else:
        manual = retrieve(
            retrieve_query,
            topology=fallback.get("experiment_type"),
            k=4,
            session_artifacts=manual_artifacts,
        )
    tool_calls.append(_tool_call("retrieve", started, manual))
    started = time.perf_counter()
    tool_calls.append(
        _tool_call(
            "request_measurement",
            started,
            {"requested": fallback.get("next_measurement", {}), "source": "catalog_planner"},
            status="stub",
        )
    )
    context = {
        "session": session,
        "measurements": evidence_measurements,
        "recent_messages": recent_messages,
        "netlist": netlist,
        "waveform": waveform,
        "manual": manual,
        "vision": vision_results,
        "comparison": comparison,
        "deterministic_diagnosis": fallback,
        "student_message": user_message,
    }
    agent_context = AgentContext(
        session=session,
        artifacts=artifacts,
        measurements=evidence_measurements,
        netlist=netlist,
        waveform=waveform,
        comparison=comparison,
        fallback=fallback,
        settings=settings,
    )

    gemma_status = "deterministic_fallback"
    diagnosis = fallback
    try:
        client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        agentic_prompt = AGENTIC_SYSTEM_PROMPT.format(
            topology=fallback.get("experiment_type", "unknown"),
            expected_behavior=json.dumps(fallback.get("expected_behavior", {}), indent=2),
            fault_candidates=json.dumps(fallback.get("likely_faults", [])[:5], indent=2),
            lang=lang,
        )
        agent_result = await _agentic_loop(
            client,
            agentic_prompt,
            STRUCTURED_DIAGNOSIS_PROMPT.format(context=json.dumps(context, indent=2)),
            recent_messages,
            TOOL_SCHEMAS,
            agent_context,
            max_iterations=4,
        )
        tool_calls.extend(agent_result["tool_calls"])
        content = agent_result["content"]
        parsed = parse_json_response(content)
        if parsed:
            diagnosis = {**fallback, **parsed, "agent_iterations": agent_result["iterations"]}
            gemma_status = "ollama_gemma_agentic" if agent_result["tool_calls"] else "ollama_gemma_single_shot"
        else:
            gemma_status = "ollama_partial"
            diagnosis = {**fallback, "agent_iterations": agent_result["iterations"]}
    except Exception as exc:  # noqa: BLE001 - fallback is the required demo behavior.
        gemma_status = "deterministic_fallback"
        diagnosis = {**fallback, "gemma_error": exc.__class__.__name__}

    return _save_diagnosis(session_id, diagnosis, tool_calls, gemma_status=gemma_status, gemma_model=settings.ollama_model)


def _save_diagnosis(
    session_id: str,
    diagnosis: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    gemma_status: str,
    gemma_model: str | None = None,
) -> dict[str, Any]:
    diagnosis = {**diagnosis, "tool_calls": tool_calls, "gemma_status": gemma_status}
    if gemma_model:
        diagnosis["gemma_model"] = gemma_model
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
