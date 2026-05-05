from pathlib import Path

from app.tools.measurement_compare import compare_expected_vs_observed
from app.tools.parse_netlist import parse_netlist_file
from app.tools.safety_check import safety_check
from app.tools.waveform_analysis import analyze_waveform_csv


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "sample_data" / "op_amp_lab"


def test_parse_netlist_computes_op_amp_gain():
    result = parse_netlist_file(SAMPLES / "opamp_inverting.net")
    assert result["detected_topology"] == "op_amp_inverting"
    assert result["computed"]["gain"] == -4.7


def test_waveform_analysis_detects_positive_saturation():
    result = analyze_waveform_csv(SAMPLES / "observed_saturated_waveform.csv")
    assert result["is_saturated"] is True
    assert result["saturation_rail"] == "positive"


def test_compare_recommends_non_inverting_input_measurement():
    comparison = compare_expected_vs_observed(-4.7, {"is_saturated": True, "saturation_rail": "positive"}, [])
    assert comparison["mismatch_type"] == "saturation_instead_of_linear_amplification"
    assert comparison["recommended_next_measurement"] == "non_inverting_input_voltage"


def test_safety_refuses_mains_debugging():
    result = safety_check("My op amp is connected to 230V AC mains")
    assert result["allowed"] is False
    assert result["risk_level"] == "high_voltage_or_mains"

