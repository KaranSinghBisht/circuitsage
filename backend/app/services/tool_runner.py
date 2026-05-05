from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..tools.rag import retrieve
from .fault_catalog import _expected_behavior


@dataclass
class AgentContext:
    session: dict[str, Any]
    artifacts: list[dict[str, Any]]
    measurements: list[dict[str, Any]]
    netlist: dict[str, Any]
    waveform: dict[str, Any]
    comparison: dict[str, Any]
    fallback: dict[str, Any]
    settings: Any


def _topology(context: AgentContext) -> str:
    return context.fallback.get("experiment_type") or context.netlist.get("detected_topology") or "unknown"


async def run_tool(name: str, arguments: dict, *, context: AgentContext) -> dict:
    arguments = arguments if isinstance(arguments, dict) else {}
    topology = _topology(context)
    top_fault = (context.fallback.get("likely_faults") or [{}])[0]

    if name == "final_answer":
        return arguments

    if name == "compute_expected_value":
        return {
            "quantity": arguments.get("quantity"),
            "expected_behavior": _expected_behavior(topology, context.netlist),
            "computed": context.netlist.get("computed", {}),
        }

    if name == "request_measurement":
        label = arguments.get("label") or context.fallback.get("next_measurement", {}).get("label")
        already_taken = any(str(label).lower() in m.get("label", "").lower() for m in context.measurements)
        return {"requested": label, "already_taken": already_taken}

    if name == "request_image":
        target = arguments.get("target", "breadboard")
        available = [
            {"id": artifact["id"], "kind": artifact["kind"], "filename": artifact["filename"]}
            for artifact in context.artifacts
            if target.lower() in artifact.get("kind", "").lower() or target.lower() in artifact.get("filename", "").lower()
        ]
        return {"requested_target": target, "available": available}

    if name == "cite_textbook":
        topic = arguments.get("topic") or top_fault.get("id") or topology
        return retrieve(str(topic), topology=topology if topology != "unknown" else None, k=3)

    if name == "verify_with_simulation":
        return {
            "fault_id": top_fault.get("id"),
            "verification_test": top_fault.get("verification_test") or context.fallback.get("next_measurement", {}).get("instruction"),
            "simulation_suggestion": "Change only the suspected fault condition in simulation and compare the expected node against the bench measurement.",
        }

    return {"error": "unknown_tool", "tool": name}
