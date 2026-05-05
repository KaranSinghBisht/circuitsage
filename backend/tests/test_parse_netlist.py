from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.parse_netlist import parse_netlist_file, parse_spice_value


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("topology", "computed_key", "expected"),
    [
        ("op_amp_inverting", "gain", -4.7),
        ("op_amp_noninverting", "gain", 11.0),
        ("rc_lowpass", "cutoff_hz", 159.155),
        ("voltage_divider", "vout_dc", 6.0),
        ("bjt_common_emitter", "base_bias_resistors", 2),
        ("full_wave_rectifier", "vout_peak_estimate", 10.6),
    ],
)
def test_parse_topology_samples(topology: str, computed_key: str, expected: float) -> None:
    result = parse_netlist_file(ROOT / "sample_data" / topology / "netlist.net")

    assert result["detected_topology"] == topology
    assert result["computed"][computed_key] == pytest.approx(expected, rel=1e-3)
    assert result["components"]
    assert result["nodes"]


def test_parse_spice_value_supports_common_suffixes() -> None:
    assert parse_spice_value("100n") == pytest.approx(100e-9)
    assert parse_spice_value("2.2meg") == pytest.approx(2.2e6)
    assert parse_spice_value("1e-3") == pytest.approx(1e-3)
    assert parse_spice_value("4.7k") == pytest.approx(4700)


def test_parse_spice_value_rejects_ambiguous_suffix() -> None:
    with pytest.raises(ValueError):
        parse_spice_value("10foo")
