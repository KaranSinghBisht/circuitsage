from __future__ import annotations

import pytest

from app.services.fault_catalog import score


TOPOLOGIES = [
    "op_amp_inverting",
    "op_amp_noninverting",
    "rc_lowpass",
    "voltage_divider",
    "bjt_common_emitter",
]


def by_id(faults: list[dict], fault_id: str) -> dict:
    return next(fault for fault in faults if fault["id"] == fault_id)


@pytest.mark.parametrize("topology", TOPOLOGIES)
def test_each_topology_has_at_least_three_scored_faults(topology: str) -> None:
    faults = score(topology, {"likely_fault_categories": []}, [])

    assert len(faults) >= 3
    assert len({fault["id"] for fault in faults}) == len(faults)


def test_op_amp_noninv_voltage_boosts_and_contradicts_floating_input() -> None:
    comparison = {"likely_fault_categories": ["reference_input"]}

    high = score("op_amp_inverting", comparison, [{"label": "V_noninv", "value": 2.8, "unit": "V", "mode": "DC"}])
    grounded = score("op_amp_inverting", comparison, [{"label": "V_noninv", "value": 0.0, "unit": "V", "mode": "DC"}])

    assert by_id(high, "floating_noninv_input")["confidence"] >= 0.85
    assert by_id(grounded, "floating_noninv_input")["confidence"] <= 0.15


def test_seeded_measurements_promote_expected_faults() -> None:
    cases = [
        (
            "rc_lowpass",
            [{"label": "output_gain_at_test_frequency", "value": 0.42, "unit": "ratio", "mode": "AC"}],
            "wrong_capacitor_value",
        ),
        ("voltage_divider", [{"label": "loaded_vout", "value": 1.8, "unit": "V", "mode": "DC"}], "load_resistance_too_low"),
        ("bjt_common_emitter", [{"label": "collector_voltage", "value": 0.2, "unit": "V", "mode": "DC"}], "incorrect_base_bias"),
        ("op_amp_noninverting", [{"label": "closed_loop_gain", "value": 1.0, "unit": "ratio", "mode": "AC"}], "rg_open"),
    ]

    for topology, measurements, expected_fault in cases:
        faults = score(topology, {"likely_fault_categories": []}, measurements)
        assert faults[0]["id"] == expected_fault
        assert faults[0]["confidence"] >= 0.85
