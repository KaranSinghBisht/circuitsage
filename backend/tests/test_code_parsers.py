from __future__ import annotations

from pathlib import Path

from app.main import _artifact_kind
from app.tools.parse_arduino import parse_arduino_file
from app.tools.parse_matlab import parse_matlab_file


ROOT = Path(__file__).resolve().parents[2]


def test_parse_arduino_blink_sketch() -> None:
    result = parse_arduino_file(ROOT / "sample_data" / "arduino_blink" / "blink.ino")

    assert result["detected_topology"] == "arduino_blink"
    assert result["blink_pin"] == "13"
    assert result["pin_modes"] == [{"pin": "13", "mode": "OUTPUT"}]
    assert result["delays_ms"] == [500, 500]


def test_parse_matlab_plot_script() -> None:
    result = parse_matlab_file(ROOT / "sample_data" / "matlab_plot" / "scope_plot.m")

    assert result["sampling_rate_hz"] == 1000
    assert {assignment["name"] for assignment in result["assignments"]} >= {"fs", "vin", "vout"}
    assert len(result["plot_calls"]) == 2
    assert result["context_lines"]


def test_artifact_kind_labels_code_files() -> None:
    assert _artifact_kind("blink.ino") == "tinkercad_code"
    assert _artifact_kind("scope_plot.m") == "matlab"
