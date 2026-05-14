"""Single-call vision + deterministic-tool chaining for the screen-aware Companion.

The Studio diagnose path runs a multi-iteration agent loop (slow, native function calling).
The Companion path is hotkey-grade: one vision call, then run the tools the model named.
This is what makes the LTspice/Tinkercad/MATLAB workflow useable instead of demo theater.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..tools.datasheet import datasheet_prompt_context, lookup_datasheet
from ..tools.rag import retrieve
from ..tools.safety_check import safety_check
from .fault_catalog import score as score_faults
from .ollama_client import OllamaClient, parse_json_response


SUPPORTED_TOPOLOGIES = (
    "op_amp_inverting",
    "op_amp_noninverting",
    "rc_lowpass",
    "voltage_divider",
    "bjt_common_emitter",
    "full_wave_rectifier",
    "active_highpass_filter",
    "op_amp_integrator",
    "op_amp_differentiator",
    "schmitt_trigger",
    "timer_555_astable",
    "nmos_low_side_switch",
    "instrumentation_amplifier",
)

WORKSPACE_HINTS: dict[str, str] = {
    "ltspice": "Look for: schematic in main canvas, component reference designators (R1, C1, U1), node labels (vin, vout, n_inv), source settings (DC/SIN/PULSE), .tran/.ac/.op directives, waveform viewer pane with probe traces.",
    "tinkercad": "Look for: breadboard wiring, pin order on chips, polarity of LEDs/electrolytics, ground rail continuity, code editor pane, simulation output pane.",
    "matlab": "Look for: plot windows, axis labels and units, transfer function definitions (tf, ss), sample rate fs assignments, FFT/spectrum displays, workspace variables.",
    "simulink": "Look for: block diagram with named blocks, sample time annotations, scope output, signal sinks, parameter dialog values.",
    "oscilloscope": "Look for: time/div, V/div, channel coupling (DC/AC), trigger source/level, cursor measurements, frequency/amplitude readouts.",
    "browser_lab": "Look for: lab manual section headings, expected vs measured tables, embedded simulator iframe, exercise prompts.",
    "electronics_workspace": "Identify visible circuit elements, measurements, and any obvious anomalies.",
}

MAX_AUTO_TOOL_RUNS = 3


def _record_call(
    tool_calls: list[dict[str, Any]],
    *,
    name: str,
    started: float,
    output: dict[str, Any],
    status: str = "ok",
    inp: dict[str, Any] | None = None,
) -> None:
    tool_calls.append(
        {
            "tool_name": name,
            "input": inp or {},
            "output": output,
            "status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000),
        }
    )


def _format_prior_turns(prior_turns: list[dict[str, Any]] | None) -> str:
    """Render last N companion turns as a compact conversation block for the prompt."""
    if not prior_turns:
        return "(none — this is the first ask in this companion session)"
    lines: list[str] = []
    for turn in prior_turns[-6:]:  # at most 3 user+assistant pairs
        role = turn.get("role", "user").upper()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role}: {content[:400]}")
    return "\n".join(lines) if lines else "(none)"


def _build_companion_prompt(
    question: str,
    workspace: str,
    app_hint: str,
    source_title: str,
    lang: str,
    prior_turns: list[dict[str, Any]] | None = None,
) -> str:
    workspace_hint = WORKSPACE_HINTS.get(workspace, WORKSPACE_HINTS["electronics_workspace"])
    topology_options = " | ".join(SUPPORTED_TOPOLOGIES) + " | unknown"
    prior_block = _format_prior_turns(prior_turns)
    return f"""You are CircuitSage Companion — an always-on local lab buddy looking at one screenshot from a student's electronics workspace.

RECENT COMPANION CONVERSATION (most recent last)
{prior_block}


WORKSPACE: {workspace}    APP HINT: {app_hint}    WINDOW: {source_title or "unknown"}
STUDENT QUESTION: {question or "(none — proactively suggest what to check)"}
RESPONSE LANGUAGE: {lang}

WHAT TO LOOK FOR
{workspace_hint}

RETURN ONE JSON OBJECT (no prose outside JSON) WITH THESE EXACT KEYS:
{{
  "visible_context": "1-3 sentences naming what is actually on screen, with explicit uncertainty markers",
  "workspace": "{workspace}",
  "detected_topology": "{topology_options}",
  "detected_components": [{{"ref": "U1", "model": "TL081"}}],
  "detected_measurements": [{{"label": "Vout", "value": 11.8, "unit": "V"}}],
  "suspected_faults": ["short hypothesis", "..."],
  "user_facing_answer": "direct help for the student in {lang}, 2-4 sentences",
  "suggested_actions": [
    {{"label": "human-readable label", "tool": "score_faults", "args": {{"topology": "op_amp_inverting"}}}},
    {{"label": "Look up TL081 datasheet", "tool": "lookup_datasheet", "args": {{"part_number": "TL081"}}}},
    {{"label": "Capture a clean shot of pin 3", "tool": "request_screenshot", "args": {{"target": "op-amp pin 3"}}}},
    {{"label": "Measure V at the non-inverting input", "tool": "request_measurement", "args": {{"label": "V_noninv"}}}}
  ],
  "confidence": "low | medium | high",
  "safety": {{"risk_level": "low_voltage_lab | high_voltage_or_mains", "warnings": ["..."]}}
}}

RULES
- Do not invent components or values that are not visibly readable. Mark uncertainty in visible_context.
- Empty arrays are valid. If you cannot read any measurements, return [].
- detected_topology MUST be "unknown" unless you can SEE a feature unique to one of the listed topologies (e.g. an op-amp triangle symbol, a clearly-marked TL081/LM741 chip, a visible RC + ground network). DO NOT pick op_amp_inverting just because the student says "not working" — most basic bulb/LED/battery circuits are NOT in the catalog and should return "unknown".
- detected_measurements MUST be empty unless you can read an actual numeric value from a meter, scope cursor, or labelled annotation in the image. Do NOT infer "12 V supply" from a 9V battery sticker. Do NOT estimate values.
- For a basic battery+bulb+breadboard circuit (no IC chips), reason about: bulb filament intact, polarity of polarized parts, broken jumper, parallel vs series wiring, insufficient voltage, loose connection. Return detected_topology: "unknown" and put these in suspected_faults.
- For LTspice with a known topology (op-amp triangle visible), suggest score_faults plus lookup_datasheet for any visible op-amp/transistor part.
- For an oscilloscope-like view, suggest request_measurement to capture the numeric reading rigorously.
- Refuse detailed live debugging for mains, high-voltage, SMPS primary, CRT/flyback, EV battery, microwave, or large capacitor banks; set safety.risk_level accordingly and leave suspected_faults empty.
- Keep JSON keys in English. Translate only user_facing_answer and any human-readable label/instruction strings.
"""


def _measurements_to_dicts(detected: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, measurement in enumerate(detected or []):
        if not isinstance(measurement, dict):
            continue
        try:
            value = float(measurement.get("value"))
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "id": f"vision_{index}",
                "label": str(measurement.get("label", "")),
                "value": value,
                "unit": str(measurement.get("unit", "V")),
                "mode": "vision_extracted",
                "context": "extracted from screenshot by Gemma vision",
                "source": "companion_vision",
            }
        )
    return out


async def _run_suggested_tools(
    parsed: dict[str, Any],
    tool_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    suggestions = list(parsed.get("suggested_actions") or [])
    detected_topology = parsed.get("detected_topology") or "unknown"
    detected_components = parsed.get("detected_components") or []
    detected_measurements = _measurements_to_dicts(parsed.get("detected_measurements") or [])

    has_score_for_topology = any(
        s.get("tool") == "score_faults"
        and (s.get("args") or {}).get("topology") in (None, detected_topology)
        for s in suggestions
    )
    if detected_topology in SUPPORTED_TOPOLOGIES and not has_score_for_topology:
        suggestions.insert(
            0,
            {
                "label": f"Score {detected_topology.replace('_', ' ')} fault catalog",
                "tool": "score_faults",
                "args": {"topology": detected_topology},
            },
        )

    runs = 0
    for suggestion in suggestions:
        if runs >= MAX_AUTO_TOOL_RUNS:
            break
        tool = suggestion.get("tool")
        args = suggestion.get("args") or {}
        label = suggestion.get("label", tool or "")

        if tool == "score_faults":
            topology = args.get("topology") or detected_topology
            if topology not in SUPPORTED_TOPOLOGIES:
                continue
            started = time.perf_counter()
            # score_faults reads JSON files from disk + runs scoring loops; offload
            # to a worker thread so the FastAPI event loop stays responsive when
            # multiple companion users hit the hosted demo concurrently.
            scored = await asyncio.to_thread(
                score_faults, topology, {"likely_fault_categories": []}, detected_measurements
            )
            output = {"topology": topology, "ranked_faults": scored[:5]}
            results.append({"tool": tool, "label": label, "args": {"topology": topology}, "result": output})
            _record_call(tool_calls, name="score_faults", started=started, output=output, inp={"topology": topology})
            runs += 1
        elif tool == "lookup_datasheet":
            part_number = args.get("part_number")
            if not part_number:
                for component in detected_components:
                    candidate = (component or {}).get("model") if isinstance(component, dict) else None
                    if candidate:
                        part_number = candidate
                        break
            if not part_number:
                continue
            started = time.perf_counter()
            datasheet = await asyncio.to_thread(lookup_datasheet, str(part_number))
            output = datasheet_prompt_context(datasheet)
            status = "missing" if datasheet.get("error") else "ok"
            results.append({"tool": tool, "label": label, "args": {"part_number": part_number}, "result": output})
            _record_call(
                tool_calls,
                name="lookup_datasheet",
                started=started,
                output=output,
                status=status,
                inp={"part_number": part_number},
            )
            runs += 1
        elif tool == "retrieve_rag":
            query = args.get("query") or args.get("topic") or " ".join(parsed.get("suspected_faults") or [])[:120]
            topology = args.get("topology") or (
                detected_topology if detected_topology in SUPPORTED_TOPOLOGIES else None
            )
            if not query:
                continue
            started = time.perf_counter()
            # retrieve() hits the on-disk vectorstore (200-800 ms cold) — must
            # not block the event loop on the hosted demo path.
            snippets = await asyncio.to_thread(retrieve, str(query), topology=topology, k=3)
            results.append(
                {"tool": tool, "label": label, "args": {"query": query, "topology": topology}, "result": snippets}
            )
            _record_call(
                tool_calls,
                name="retrieve_rag",
                started=started,
                output=snippets,
                inp={"query": query, "topology": topology},
            )
            runs += 1
        # request_screenshot and request_measurement are user-facing only — passed through to next_actions.

    return results


def _compose_actions(
    parsed: dict[str, Any], tool_results: list[dict[str, Any]]
) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (legacy next_actions strings, typed actions for P3 click-to-act)."""
    typed: list[dict[str, Any]] = []
    legacy: list[str] = []

    for suggestion in parsed.get("suggested_actions") or []:
        tool = suggestion.get("tool")
        label = str(suggestion.get("label", "")).strip()
        args = suggestion.get("args") or {}
        if not label:
            continue
        legacy.append(label)
        if tool in {"request_screenshot"}:
            typed.append({"label": label, "action": "capture", "args": args})
        elif tool == "request_measurement":
            typed.append({"label": label, "action": "measurement", "args": args})
        elif tool in {"score_faults", "lookup_datasheet", "retrieve_rag"}:
            already_ran = any(r.get("tool") == tool for r in tool_results)
            typed.append(
                {
                    "label": label,
                    "action": "tool_call",
                    "args": {"tool": tool, "already_ran": already_ran, **args},
                }
            )

    if not legacy and tool_results:
        for result in tool_results:
            legacy.append(result.get("label") or result.get("tool", ""))

    return legacy[:5], typed[:5]


def _compose_answer(parsed: dict[str, Any], tool_results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    base = (parsed.get("user_facing_answer") or parsed.get("answer") or "").strip()
    if base:
        parts.append(base)

    for result in tool_results:
        if result["tool"] == "score_faults":
            ranked = (result["result"] or {}).get("ranked_faults") or []
            if ranked:
                top = ranked[0]
                parts.append(
                    f"Top catalog match: **{top.get('name', 'unknown')}** "
                    f"(confidence {top.get('confidence', 0)}). {top.get('why', '')}"
                )
        elif result["tool"] == "lookup_datasheet":
            datasheet = result["result"] or {}
            if not datasheet.get("error"):
                summary = (datasheet.get("summary") or "").strip().splitlines()
                first_line = summary[0] if summary else ""
                parts.append(f"Datasheet: **{datasheet.get('part_number')}** — {first_line[:200]}")
        elif result["tool"] == "retrieve_rag":
            snippets = (result["result"] or {}).get("snippets") or []
            if snippets:
                top = snippets[0]
                excerpt = (top.get("text") or "").replace("\n", " ")[:160]
                parts.append(f"Manual: *{top.get('source', '')}* — {excerpt}")

    return "\n\n".join(parts) if parts else "No insight produced; capture a clearer screenshot or add the topology."


def _safety_refusal_response(
    workspace: str,
    safety: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    started_total: float,
    saved_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "mode": "safety_refusal",
        "workspace": workspace,
        "visible_context": "Screen analysis stopped because high-voltage or mains risk was mentioned.",
        "user_facing_answer": safety["message"],
        "answer": safety["message"],
        "next_actions": ["Power down and ask an instructor or qualified technician."],
        "actions": [],
        "suggested_actions": [],
        "detected_topology": "unknown",
        "detected_components": [],
        "detected_measurements": [],
        "suspected_faults": [],
        "tool_results": [],
        "tool_calls": tool_calls,
        "can_click": False,
        "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
        "confidence": "high",
        "saved_artifact": saved_artifact,
        "duration_ms": round((time.perf_counter() - started_total) * 1000),
    }


def _no_image_response(
    workspace: str,
    safety: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    started_total: float,
    saved_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    capture_label = "Press the hotkey (Cmd+Shift+Space) to capture the active window"
    return {
        "mode": "deterministic_fallback",
        "workspace": workspace,
        "visible_context": "No screenshot was provided.",
        "user_facing_answer": (
            "I cannot reason about a circuit without visual or measurement evidence. "
            "Capture a screenshot of your workspace and ask again."
        ),
        "answer": "Capture a screenshot of your workspace and ask again.",
        "next_actions": [capture_label],
        "actions": [{"label": capture_label, "action": "capture", "args": {}}],
        "suggested_actions": [],
        "detected_topology": "unknown",
        "detected_components": [],
        "detected_measurements": [],
        "suspected_faults": [],
        "tool_results": [],
        "tool_calls": tool_calls,
        "can_click": True,
        "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
        "confidence": "low",
        "saved_artifact": saved_artifact,
        "duration_ms": round((time.perf_counter() - started_total) * 1000),
    }


def _vision_failed_response(
    workspace: str,
    safety: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    exc: Exception,
    started_total: float,
    saved_artifact: dict[str, Any] | None,
    vision_model: str,
) -> dict[str, Any]:
    return {
        "mode": "deterministic_fallback",
        "workspace": workspace,
        "visible_context": "Vision call to local Gemma failed.",
        "user_facing_answer": (
            "I couldn't reach the local vision model. Check that Ollama is running and the vision model is pulled."
        ),
        "answer": "Vision unavailable — check Ollama.",
        "next_actions": [f"Run: ollama pull {vision_model}"],
        "actions": [],
        "suggested_actions": [],
        "detected_topology": "unknown",
        "detected_components": [],
        "detected_measurements": [],
        "suspected_faults": [],
        "tool_results": [],
        "tool_calls": tool_calls,
        "gemma_error": f"{exc.__class__.__name__}: {exc}",
        "can_click": False,
        "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
        "confidence": "low",
        "saved_artifact": saved_artifact,
        "duration_ms": round((time.perf_counter() - started_total) * 1000),
    }


def _unparsed_vision_response(
    workspace: str,
    safety: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    raw: str,
    started_total: float,
    saved_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    excerpt = (raw or "").strip()[:600]
    return {
        "mode": "gemma_text_unparsed",
        "workspace": workspace,
        "visible_context": excerpt,
        "user_facing_answer": excerpt,
        "answer": excerpt,
        "next_actions": ["Re-ask with a tighter question; the model returned prose instead of JSON."],
        "actions": [],
        "suggested_actions": [],
        "detected_topology": "unknown",
        "detected_components": [],
        "detected_measurements": [],
        "suspected_faults": [],
        "tool_results": [],
        "tool_calls": tool_calls,
        "raw": (raw or "")[:1200],
        "can_click": False,
        "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
        "confidence": "low",
        "saved_artifact": saved_artifact,
        "duration_ms": round((time.perf_counter() - started_total) * 1000),
    }


async def analyze(
    *,
    question: str,
    image_base64: str | None,
    workspace: str,
    app_hint: str,
    source_title: str,
    lang: str,
    settings: Any,
    saved_artifact: dict[str, Any] | None = None,
    prior_turns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the single-call vision + tool-chaining loop. Returns the response dict."""
    started_total = time.perf_counter()
    tool_calls: list[dict[str, Any]] = []

    safety_started = time.perf_counter()
    safety = safety_check(question or "")
    _record_call(
        tool_calls,
        name="safety_check",
        started=safety_started,
        output=safety,
        inp={"text_only": True},
    )

    if not safety["allowed"]:
        return _safety_refusal_response(workspace, safety, tool_calls, started_total, saved_artifact)

    if not image_base64:
        return _no_image_response(workspace, safety, tool_calls, started_total, saved_artifact)

    prompt = _build_companion_prompt(question, workspace, app_hint, source_title, lang, prior_turns)
    client = OllamaClient(settings.ollama_base_url, settings.ollama_vision_model)

    vision_started = time.perf_counter()
    try:
        chat = await client.chat(
            [{"role": "user", "content": prompt, "images": [image_base64]}],
            format_json=True,
        )
    except Exception as exc:  # noqa: BLE001 - graceful degrade is required when Ollama is missing.
        return _vision_failed_response(
            workspace, safety, tool_calls, exc, started_total, saved_artifact, settings.ollama_vision_model
        )

    _record_call(
        tool_calls,
        name="vision_analyze",
        started=vision_started,
        output={
            "model": settings.ollama_vision_model,
            "raw_status": chat.get("raw_status"),
            "fallback_no_format": chat.get("fallback", False),
        },
        inp={"workspace": workspace},
    )

    parsed = parse_json_response(chat.get("content", ""))
    if not parsed:
        return _unparsed_vision_response(
            workspace, safety, tool_calls, chat.get("content", ""), started_total, saved_artifact
        )

    tool_results = await _run_suggested_tools(parsed, tool_calls)
    legacy_actions, typed_actions = _compose_actions(parsed, tool_results)
    composed_answer = _compose_answer(parsed, tool_results)

    response_safety = parsed.get("safety") or {
        "risk_level": safety["risk_level"],
        "warnings": safety["warnings"],
    }

    return {
        "mode": "ollama_gemma_vision",
        "workspace": parsed.get("workspace") or workspace,
        "visible_context": parsed.get("visible_context", ""),
        "user_facing_answer": composed_answer,
        "answer": composed_answer,
        "detected_topology": parsed.get("detected_topology", "unknown"),
        "detected_components": parsed.get("detected_components") or [],
        "detected_measurements": parsed.get("detected_measurements") or [],
        "suspected_faults": parsed.get("suspected_faults") or [],
        "next_actions": legacy_actions,
        "actions": typed_actions,
        "suggested_actions": parsed.get("suggested_actions") or [],
        "tool_results": tool_results,
        "tool_calls": tool_calls,
        "can_click": bool(typed_actions),
        "safety": response_safety,
        "confidence": parsed.get("confidence", "low"),
        "saved_artifact": saved_artifact,
        "duration_ms": round((time.perf_counter() - started_total) * 1000),
    }
