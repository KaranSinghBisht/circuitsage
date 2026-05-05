from __future__ import annotations

from typing import Any


Fault = dict[str, Any]


CATALOG: dict[str, dict[str, Any]] = {
    "op_amp_inverting": {
        "label": "Inverting op-amp amplifier",
        "faults": [
            {
                "id": "floating_noninverting_input",
                "name": "Floating or incorrectly biased non-inverting input",
                "category": "reference_input",
                "base_confidence": 0.58,
                "why": "A missing 0 V reference on the non-inverting input can force the op-amp output into rail saturation even when the feedback resistor ratio is correct.",
                "requires_measurements": ["non_inverting_input_voltage"],
                "verification_test": "Measure the non-inverting input with respect to circuit ground.",
                "next_without_measurement": {
                    "label": "Voltage at non-inverting input pin",
                    "expected": "approximately 0 V",
                    "instruction": "Measure the non-inverting input with respect to circuit ground before changing resistor values.",
                },
                "next_after_measurement": {
                    "label": "Retest Vout after grounding non-inverting input",
                    "expected": "inverted sine wave near the computed closed-loop gain",
                    "instruction": "Power off, tie the non-inverting input to circuit ground, power on, and retest the output waveform.",
                },
            },
            {
                "id": "missing_feedback",
                "name": "Feedback path disconnected or wired to the wrong node",
                "category": "feedback",
                "base_confidence": 0.42,
                "why": "Without negative feedback from output to the inverting input, an op-amp behaves like a comparator and can latch near a rail.",
                "requires_measurements": ["feedback_continuity"],
                "verification_test": "Power off and ohm-meter Rf between Vout and the inverting input node.",
                "next_without_measurement": {
                    "label": "Feedback resistor continuity",
                    "expected": "Rf connects from Vout to the inverting input node",
                    "instruction": "Power off and verify continuity from the output node through Rf to the inverting input node.",
                },
            },
            {
                "id": "rail_imbalance",
                "name": "Power rail or common ground issue",
                "category": "power_rails",
                "base_confidence": 0.28,
                "why": "A missing common ground or rail reference can make otherwise correct node voltages appear inconsistent at the bench.",
                "requires_measurements": ["v_supply_pos", "v_supply_neg", "v_ground"],
                "verification_test": "Measure both rails with respect to the circuit ground/reference node.",
                "next_without_measurement": {
                    "label": "Common ground continuity",
                    "expected": "signal source, circuit ground, and supply reference share one 0 V node",
                    "instruction": "Power off and check continuity between the function generator ground, breadboard ground, and supply midpoint/reference.",
                },
            },
        ],
    },
    "unknown": {
        "label": "Unknown circuit",
        "faults": [
            {
                "id": "unknown_reference_or_ground",
                "name": "Reference or ground mismatch",
                "category": "common_ground",
                "base_confidence": 0.34,
                "why": "Many low-voltage lab faults come from measuring against a different reference than the circuit or simulator assumes.",
                "next_without_measurement": {
                    "label": "Ground/reference map",
                    "expected": "one named reference node for every measurement",
                    "instruction": "Identify the circuit ground/reference node and repeat the key input/output measurement against that node.",
                },
            },
            {
                "id": "unknown_missing_evidence",
                "name": "Insufficient circuit evidence",
                "category": "unknown",
                "base_confidence": 0.24,
                "why": "CircuitSage needs the topology, expected behavior, and observed node measurement before it can rank a specific component fault.",
                "next_without_measurement": {
                    "label": "Circuit topology and symptom",
                    "expected": "netlist/schematic plus one expected-vs-observed measurement",
                    "instruction": "Upload a netlist or screenshot and add the measured node, value, unit, and expected value.",
                },
            },
        ],
    },
}


def _measurement_by_tokens(measurements: list[dict[str, Any]], tokens: tuple[str, ...]) -> dict[str, Any] | None:
    for measurement in measurements:
        label = measurement.get("label", "").lower()
        if any(token in label for token in tokens):
            return measurement
    return None


def candidates(topology: str, comparison: dict[str, Any] | None = None) -> list[Fault]:
    if topology not in CATALOG or topology == "unknown":
        return []
    return CATALOG[topology]["faults"]


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


def _rank_faults(
    topology: str,
    comparison: dict[str, Any],
    measurements: list[dict[str, Any]],
) -> list[Fault]:
    catalog = CATALOG.get(topology, CATALOG["unknown"])
    categories = set(comparison.get("likely_fault_categories", []))
    mismatch_type = comparison.get("mismatch_type")
    noninv = _measurement_by_tokens(measurements, ("non", "pin 3", "v_noninv"))

    ranked: list[Fault] = []
    for fault in catalog["faults"]:
        score = float(fault["base_confidence"])
        if fault["category"] in categories:
            score += 0.12
        if mismatch_type == "saturation_instead_of_linear_amplification" and topology.startswith("op_amp"):
            score += 0.08
        if fault["id"] == "floating_noninverting_input" and noninv:
            try:
                if abs(float(noninv["value"])) > 0.5:
                    score += 0.16
            except (TypeError, ValueError):
                pass
        next_measurement = fault.get("next_without_measurement", {})
        if fault["id"] == "floating_noninverting_input" and noninv:
            next_measurement = fault.get("next_after_measurement", next_measurement)

        ranked.append(
            {
                "id": fault["id"],
                "name": fault["name"],
                "fault": fault["name"],
                "confidence": round(min(score, 0.96), 2),
                "why": fault["why"],
                "category": fault["category"],
                "next_measurement": next_measurement,
            }
        )
    return sorted(ranked, key=lambda item: item["confidence"], reverse=True)


def _expected_behavior(topology: str, netlist: dict[str, Any]) -> dict[str, Any]:
    computed = netlist.get("computed", {})
    if topology == "op_amp_inverting":
        gain = computed.get("gain")
        behavior: dict[str, Any] = {"gain": gain}
        if isinstance(gain, int | float):
            behavior["output"] = f"inverted sine wave, about {abs(gain)} V peak for 1 V peak input"
        else:
            behavior["output"] = "inverted output set by -Rf/Rin if the feedback network is intact"
        return behavior
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

    likely_faults = _rank_faults(topology, comparison, measurements)
    top_fault = likely_faults[0] if likely_faults else None
    next_measurement = (
        top_fault.get("next_measurement")
        if top_fault
        else CATALOG["unknown"]["faults"][0]["next_without_measurement"]
    )

    confidence = "medium"
    status = "diagnosing"
    if top_fault and top_fault["confidence"] >= 0.8:
        confidence = "high"
        status = "resolved" if topology != "unknown" else "diagnosing"
    elif topology == "unknown":
        confidence = "low"

    explanation = (
        f"The strongest catalog match is {top_fault['name']}. {top_fault['why']}"
        if top_fault
        else "CircuitSage needs more topology and measurement evidence before ranking a fault."
    )
    if topology == "unknown":
        explanation = (
            "I do not have enough topology information to make an op-amp-specific claim. "
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
