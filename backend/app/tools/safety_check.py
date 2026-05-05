from __future__ import annotations

import re


HIGH_RISK_PATTERNS = [
    r"\bmains\b",
    r"\b110\s*v\b",
    r"\b120\s*v\b",
    r"\b220\s*v\b",
    r"\b230\s*v\b",
    r"\b240\s*v\b",
    r"wall outlet",
    r"transformer primary",
    r"smps primary",
    r"\bcrt\b",
    r"flyback",
    r"microwave",
    r"ev battery",
    r"capacitor bank",
]


def safety_check(text: str) -> dict[str, object]:
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in HIGH_RISK_PATTERNS):
        return {
            "risk_level": "high_voltage_or_mains",
            "allowed": False,
            "message": (
                "CircuitSage is only for low-voltage educational circuits. This may involve dangerous "
                "voltage/current. Power down and ask an instructor or qualified technician. I can help "
                "with theory or a de-energized schematic, but not live debugging."
            ),
            "warnings": ["Do not debug live mains circuits with CircuitSage."],
        }
    caution = []
    if "capacitor" in lowered:
        caution.append("Capacitors may hold charge after power is removed.")
    if "hot" in lowered or "smoke" in lowered:
        caution.append("Power off before touching or rewiring hot components.")
    return {
        "risk_level": "low_voltage_lab",
        "allowed": True,
        "message": "Low-voltage educational debugging is allowed.",
        "warnings": caution
        or ["Do not debug live mains circuits with CircuitSage.", "Power off before rewiring the op-amp pins."],
    }

