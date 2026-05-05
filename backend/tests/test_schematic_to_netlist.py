from __future__ import annotations

import asyncio

from app.services.demo_seeds import _demo_seed_op_amp_netlist
from app.services.netlist_validator import validate_netlist_text
from app.tools.schematic_to_netlist import recognize_schematic


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


def test_demo_seed_op_amp_netlist_parses_to_gain() -> None:
    result = _demo_seed_op_amp_netlist()
    assert result["mode"] == "demo_seed"
    assert result["detected_topology"] == "op_amp_inverting"
    assert result["parsed"]["computed"]["gain"] == -4.7


def test_vision_unavailable_does_not_fabricate_hint_netlist(monkeypatch) -> None:
    async def fail_chat(self, messages, format_json=False, tools=None):
        raise RuntimeError("vision down")

    monkeypatch.setattr("app.tools.schematic_to_netlist.OllamaClient.chat", fail_chat)
    result = asyncio.run(recognize_schematic("ZmFrZQ==", hint="opamp inverting amplifier"))
    assert result["detected_topology"] == "unknown"
    assert result["confidence"] == 0.0
    assert result["mode"] == "vision_unavailable"
    assert result["netlist"] == ""
    assert result["missing"]
