from __future__ import annotations

from app.services.netlist_validator import validate_netlist_text
from app.tools.schematic_to_netlist import recognize_schematic_sync_fallback


def test_validate_recognized_op_amp_netlist() -> None:
    netlist = """
Vin vin 0 SIN(0 1 1k)
Rin vin n_inv 10k
Rf vout n_inv 47k
Vcc vcc 0 DC 12
Vee vee 0 DC -12
E1 vout 0 n_noninv n_inv 100000
Rbias n_noninv 0 1meg
"""
    result = validate_netlist_text(netlist, confidence=0.88)
    assert result["detected_topology"] == "op_amp_inverting"
    assert result["confidence"] == 0.88
    assert result["parsed"]["computed"]["gain"] == -4.7


def test_ambiguous_schematic_fallback_stays_low_confidence() -> None:
    result = recognize_schematic_sync_fallback("blurred unknown circuit")
    assert result["detected_topology"] == "unknown"
    assert result["confidence"] == 0.0
    assert result["missing"]
