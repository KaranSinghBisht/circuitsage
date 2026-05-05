from __future__ import annotations

from typing import Any


def compare_expected_vs_observed(
    expected_gain: float | None,
    observed_summary: dict[str, Any] | None,
    measurements: list[dict[str, Any]],
) -> dict[str, Any]:
    labels = {m["label"].lower(): m for m in measurements}
    if observed_summary and observed_summary.get("is_saturated"):
        rail = observed_summary.get("saturation_rail") or "unknown"
        next_key = "non_inverting_input_voltage"
        if not any("non" in key or "pin 3" in key or "v_noninv" in key for key in labels):
            recommended = "non_inverting_input_voltage"
        else:
            recommended = "feedback_continuity_or_reference_ground"
        return {
            "mismatch_type": "saturation_instead_of_linear_amplification",
            "expected_gain": expected_gain,
            "observed_rail": rail,
            "likely_fault_categories": ["reference_input", "feedback", "power_rails", "common_ground"],
            "recommended_next_measurement": recommended or next_key,
        }

    return {
        "mismatch_type": "needs_more_evidence",
        "expected_gain": expected_gain,
        "likely_fault_categories": ["unknown"],
        "recommended_next_measurement": "vout_dc_and_supply_rails",
    }

