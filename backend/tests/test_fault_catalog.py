from __future__ import annotations

from app.services.fault_catalog import CATALOG, build_catalog_diagnosis
from app.tools.measurement_compare import compare_expected_vs_observed
from app.tools.parse_netlist import parse_netlist_file
from app.tools.waveform_analysis import analyze_waveform_csv

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "sample_data" / "op_amp_lab"


def test_op_amp_catalog_contains_seed_fault() -> None:
    fault_ids = {fault["id"] for fault in CATALOG["op_amp_inverting"]["faults"]}
    assert "op_amp_reference_input_floating" in fault_ids


def test_catalog_ranks_op_amp_reference_fault_for_seed_case() -> None:
    netlist = parse_netlist_file(SAMPLES / "opamp_inverting.net")
    waveform = analyze_waveform_csv(SAMPLES / "observed_saturated_waveform.csv")
    measurements = [
        {"label": "Vout", "value": 11.8, "unit": "V", "mode": "DC"},
        {"label": "V+", "value": 12.1, "unit": "V", "mode": "DC"},
        {"label": "V-", "value": -12.0, "unit": "V", "mode": "DC"},
    ]
    comparison = compare_expected_vs_observed(netlist["computed"]["gain"], waveform, measurements)

    diagnosis = build_catalog_diagnosis(
        {"experiment_type": "op_amp_inverting"},
        netlist,
        waveform,
        comparison,
        measurements,
        {"risk_level": "low_voltage_lab", "warnings": []},
    )

    top_fault = diagnosis["likely_faults"][0]
    assert top_fault["id"] == "op_amp_reference_input_floating"
    assert top_fault["name"] == "Floating or incorrectly biased non-inverting input"
    assert diagnosis["next_measurement"]["label"] == "Voltage at non-inverting input pin"


def test_catalog_uses_confirmation_step_after_reference_measurement() -> None:
    netlist = parse_netlist_file(SAMPLES / "opamp_inverting.net")
    waveform = analyze_waveform_csv(SAMPLES / "observed_saturated_waveform.csv")
    measurements = [{"label": "V_noninv", "value": 2.8, "unit": "V", "mode": "DC"}]
    comparison = compare_expected_vs_observed(netlist["computed"]["gain"], waveform, measurements)

    diagnosis = build_catalog_diagnosis(
        {"experiment_type": "op_amp_inverting"},
        netlist,
        waveform,
        comparison,
        measurements,
        {"risk_level": "low_voltage_lab", "warnings": []},
    )

    assert diagnosis["likely_faults"][0]["id"] == "op_amp_reference_input_floating"
    assert diagnosis["next_measurement"]["label"] == "Retest Vout after grounding non-inverting input"
    assert diagnosis["session_status"] == "resolved"
