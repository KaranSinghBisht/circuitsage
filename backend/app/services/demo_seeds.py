from __future__ import annotations

from typing import Any

from .netlist_validator import validate_netlist_text


def _demo_seed_op_amp_netlist() -> dict[str, Any]:
    netlist = "\n".join(
        [
            "Vin vin 0 SIN(0 1 1k)",
            "Rin vin n_inv 10k",
            "Rf vout n_inv 47k",
            "Vcc vcc 0 DC 12",
            "Vee vee 0 DC -12",
            "E1 vout 0 n_noninv n_inv 100000",
            "Rbias n_noninv 0 1meg",
        ]
    )
    result = validate_netlist_text(netlist, confidence=0.62)
    result["mode"] = "demo_seed"
    return result
