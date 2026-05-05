from __future__ import annotations

import json
from pathlib import Path
from typing import Any


Fault = dict[str, Any]
ScoredFault = dict[str, Any]
DATA_DIR = Path(__file__).with_name("fault_data")

MEASUREMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "non_inverting_input_voltage": ("non", "v_noninv", "pin 3"),
    "closed_loop_gain": ("gain", "closed_loop_gain"),
    "output_gain_at_test_frequency": ("gain", "attenuation", "vout/vin"),
    "loaded_vout": ("loaded_vout", "vout", "output"),
    "collector_voltage": ("collector", "vc"),
}

MEASUREMENT_LABELS = {
    "non_inverting_input_voltage": "Voltage at non-inverting input pin",
    "feedback_continuity": "Feedback resistor continuity",
    "loaded_vout": "Loaded output voltage",
    "collector_voltage": "Collector DC voltage",
    "closed_loop_gain": "Closed-loop gain",
    "output_gain_at_test_frequency": "Output gain at test frequency",
}

UNKNOWN_CATALOG: dict[str, Any] = {
    "label": "Unknown circuit",
    "faults": [
        {
            "id": "unknown_reference_or_ground",
            "name": "Reference or ground mismatch",
            "category": "common_ground",
            "base_confidence": 0.34,
            "why": "Many low-voltage lab faults come from measuring against a different reference than the circuit or simulator assumes.",
            "requires_measurements": ["ground_reference"],
            "verification_test": "Identify the circuit ground/reference node and repeat the key input/output measurement against that node.",
            "fix_recipe": "Anchor every measurement to the same reference node.",
        },
        {
            "id": "unknown_missing_evidence",
            "name": "Insufficient circuit evidence",
            "category": "unknown",
            "base_confidence": 0.24,
            "why": "CircuitSage needs the topology, expected behavior, and observed node measurement before it can rank a specific component fault.",
            "requires_measurements": ["circuit_topology", "observed_node"],
            "verification_test": "Upload a netlist or screenshot and add the measured node, value, unit, and expected value.",
            "fix_recipe": "Collect topology and one expected-vs-observed measurement.",
        },
    ],
}


def _load_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for path in sorted(DATA_DIR.glob("*.json")):
        catalog[path.stem] = json.loads(path.read_text())
    catalog["unknown"] = UNKNOWN_CATALOG
    return catalog


CATALOG = _load_catalog()


def _measurement_tokens(measurement_key: str) -> tuple[str, ...]:
    return MEASUREMENT_ALIASES.get(measurement_key, (measurement_key.lower(), measurement_key.lower().replace("_", " ")))


def _measurement_by_key(measurements: list[dict[str, Any]], measurement_key: str) -> dict[str, Any] | None:
    tokens = _measurement_tokens(measurement_key)
    for measurement in measurements:
        label = measurement.get("label", "").lower()
        if any(token in label for token in tokens):
            return measurement
    return None


def _signature_matches(signature: dict[str, Any], measurements: list[dict[str, Any]]) -> bool | None:
    measurement = _measurement_by_key(measurements, signature["measurement"])
    if not measurement:
        return None
    try:
        observed = float(measurement["value"])
        threshold = float(signature["value"])
    except (KeyError, TypeError, ValueError):
        return None
    operator = signature.get("operator")
    if operator == "abs_gt":
        return abs(observed) > threshold
    if operator == "abs_lte":
        return abs(observed) <= threshold
    if operator == "lt":
        return observed < threshold
    if operator == "lte":
        return observed <= threshold
    if operator == "gt":
        return observed > threshold
    if operator == "gte":
        return observed >= threshold
    return None


def candidates(topology: str, comparison: dict[str, Any] | None = None) -> list[Fault]:
    if topology not in CATALOG or topology == "unknown":
        return []
    return CATALOG[topology]["faults"]


def score(topology: str, comparison: dict[str, Any], measurements: list[dict[str, Any]]) -> list[ScoredFault]:
    catalog = CATALOG.get(topology, CATALOG["unknown"])
    categories = set(comparison.get("likely_fault_categories", []))
    scored: list[ScoredFault] = []
    for fault in catalog["faults"]:
        confidence = float(fault["base_confidence"])
        if fault.get("category") in categories:
            confidence += 0.1

        signature_result = None
        if "signature" in fault:
            signature_result = _signature_matches(fault["signature"], measurements)
            if signature_result is True:
                confidence = max(confidence + 0.25, 0.85)
            elif signature_result is False:
                confidence = min(confidence, 0.15)

        confidence = round(min(confidence, 0.92), 2)
        scored.append(
            {
                "id": fault["id"],
                "name": fault["name"],
                "fault": fault["name"],
                "confidence": confidence,
                "why": fault["why"],
                "category": fault.get("category", "unknown"),
                "requires_measurements": fault.get("requires_measurements", []),
                "verification_test": fault.get("verification_test", ""),
                "fix_recipe": fault.get("fix_recipe", ""),
                "signature_matched": signature_result,
                "next_measurement": _next_for_fault(fault),
            }
        )
    return sorted(scored, key=lambda item: item["confidence"], reverse=True)


def planner_next_measurement(topology: str, taken: set[str]) -> dict[str, str]:
    for fault in candidates(topology):
        for needed in fault.get("requires_measurements", []):
            if needed not in taken:
                return {
                    "label": needed,
                    "expected": "topology-dependent",
                    "instruction": f"Measure {needed} per the verification test for '{fault['name']}'.",
                }
    return {
        "label": "general_inspection",
        "expected": "documented bench observation",
        "instruction": "Inspect supply rails, ground reference, and feedback continuity.",
    }


def _next_for_fault(fault: Fault) -> dict[str, str]:
    needed = fault.get("requires_measurements", ["general_inspection"])[0]
    return {
        "label": MEASUREMENT_LABELS.get(needed, needed),
        "expected": "topology-dependent",
        "instruction": fault.get("verification_test") or f"Measure {needed}.",
    }


def _expected_behavior(topology: str, netlist: dict[str, Any]) -> dict[str, Any]:
    computed = netlist.get("computed", {})
    if topology in {"op_amp_inverting", "op_amp_noninverting"}:
        gain = computed.get("gain")
        behavior: dict[str, Any] = {"gain": gain}
        if isinstance(gain, int | float):
            if topology == "op_amp_inverting":
                behavior["output"] = f"inverted sine wave, about {abs(gain)} V peak for 1 V peak input"
            else:
                behavior["output"] = f"non-inverted sine wave, about {abs(gain)} V peak for 1 V peak input"
        return behavior
    if topology == "rc_lowpass":
        return {"cutoff_hz": computed.get("cutoff_hz"), "summary": "low frequencies pass; high frequencies attenuate"}
    if topology == "voltage_divider":
        return {"vout_dc": computed.get("vout_dc"), "ratio": computed.get("ratio")}
    if topology == "bjt_common_emitter":
        return {"summary": "collector biased in active region with inverted AC gain", **computed}
    if topology == "full_wave_rectifier":
        return {"summary": "positive rectified output after two diode drops", **computed}
    return {
        "summary": "Circuit topology is not identified yet.",
        "needed": ["netlist or schematic", "expected behavior", "observed node measurement"],
    }


def _observed_behavior(waveform: dict[str, Any], comparison: dict[str, Any], measurements: list[dict[str, Any]]) -> dict[str, Any]:
    if waveform.get("is_saturated"):
        rail = waveform.get("saturation_rail", "a")
        summary = f"Output is stuck near the {rail} supply rail"
    elif comparison.get("mismatch_type") == "needs_more_evidence":
        summary = "More bench evidence is needed"
    else:
        summary = "Observed behavior differs from the expected circuit behavior"
    return {
        "summary": summary,
        "evidence": [
            *(f"{m['label']} = {m['value']} {m['unit']} {m['mode']}" for m in measurements),
            f"comparison: {comparison.get('mismatch_type')}",
        ],
    }


def build_catalog_diagnosis(
    session: dict[str, Any],
    netlist: dict[str, Any],
    waveform: dict[str, Any],
    comparison: dict[str, Any],
    measurements: list[dict[str, Any]],
    safety: dict[str, Any],
) -> dict[str, Any]:
    topology = netlist.get("detected_topology") or session.get("experiment_type") or "unknown"
    if topology not in CATALOG:
        topology = "unknown"

    likely_faults = score(topology, comparison, measurements)
    top_fault = likely_faults[0] if likely_faults else None
    next_measurement = top_fault.get("next_measurement") if top_fault else _next_for_fault(UNKNOWN_CATALOG["faults"][0])

    confidence = "medium"
    status = "diagnosing"
    if top_fault and top_fault["confidence"] >= 0.8:
        confidence = "high"
        status = "resolved" if topology != "unknown" and top_fault.get("signature_matched") else "diagnosing"
    elif topology == "unknown":
        confidence = "low"

    explanation = (
        f"The strongest catalog match is {top_fault['name']}. {top_fault['why']}"
        if top_fault
        else "CircuitSage needs more topology and measurement evidence before ranking a fault."
    )
    if topology == "unknown":
        explanation = (
            "I do not have enough topology information to make a topology-specific claim. "
            "Start by anchoring the reference node and uploading a netlist, schematic, or screenshot."
        )

    return {
        "experiment_type": topology,
        "expected_behavior": _expected_behavior(topology, netlist),
        "observed_behavior": _observed_behavior(waveform, comparison, measurements),
        "likely_faults": likely_faults,
        "next_measurement": next_measurement,
        "safety": {"risk_level": safety["risk_level"], "warnings": safety["warnings"]},
        "student_explanation": explanation,
        "confidence": confidence,
        "session_status": status,
    }
