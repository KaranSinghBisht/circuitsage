from __future__ import annotations

import re


# All patterns are matched case-insensitively against the full input text. Patterns
# use explicit word boundaries (or punctuation/whitespace anchors) so we don't trip
# false positives on unrelated identifiers like "screenshot" / "hotkey" / "photo".
HIGH_RISK_PATTERNS = [
    # Mains, line, AC, high-voltage prose — all the ways a student might describe it.
    r"\bmains\b",
    r"\bline\s*voltage\b",
    r"\bhigh\s*voltage\b",
    r"\bhigh\s*tension\b",
    r"\bHV\b",
    r"\bmains\s*power\b",
    r"\bAC\s*mains\b",
    # Specific voltages — \d{2,3} catches 110/120/220/230/240/277, with optional
    # trailing AC/RMS/DC suffixes. \D anchor avoids matching "1100" or part numbers.
    r"(?:^|[^\d])(?:1[12]0|2[234]0|277)\s*v(?:ac|rms)?(?![a-rt-z])",
    # Mains frequencies are a strong signal even without "V".
    r"\b(?:50|60)\s*hz\s*mains\b",
    # Power infrastructure
    r"\bwall\s*outlet\b",
    r"\bwall\s*socket\b",
    r"\b(?:transformer\s*primary|primary\s*winding)\b",
    r"\bstep[-\s]?down\s*transformer\b",
    r"\bsmps\s*primary\b",
    # Stored-energy hazards
    r"\bCRT\b",
    r"\bflyback\b",
    r"\bmicrowave\s*(?:oven|magnetron)?\b",
    r"\bEV\s*(?:pack|battery)\b",
    r"\bcapacitor\s*bank\b",
    r"\bneon\s*(?:sign|transformer)\b",
]
HIGH_RISK_REGEX = re.compile("|".join(HIGH_RISK_PATTERNS), re.IGNORECASE)

# Cautions — also word-bounded. "hot" must be standalone (not "screenshot"); "smoke"
# similarly. "capacitor" gets a caution about stored charge but doesn't refuse.
_CAUTION_HOT = re.compile(r"\b(?:hot|smoke|burning|smell|sparks?)\b", re.IGNORECASE)
_CAUTION_CAP = re.compile(r"\bcapacitors?\b", re.IGNORECASE)


def safety_check(text: str) -> dict[str, object]:
    """Word-bounded safety screen for the Companion + Studio prompts.

    Refuses the request entirely on any high-risk pattern (mains, HV, stored
    charge in fly-back / capacitor bank / EV battery, etc.).

    Cautions (returned as warnings, request still allowed) for words that
    suggest active heat / spark / smoke or for capacitor mentions.
    """
    if not text:
        return {
            "risk_level": "low_voltage_lab",
            "allowed": True,
            "message": "Low-voltage educational debugging is allowed.",
            "warnings": [
                "Do not debug live mains circuits with CircuitSage.",
                "Power off before rewiring the op-amp pins.",
            ],
        }

    if HIGH_RISK_REGEX.search(text):
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

    caution: list[str] = []
    if _CAUTION_CAP.search(text):
        caution.append("Capacitors may hold charge after power is removed.")
    if _CAUTION_HOT.search(text):
        caution.append("Power off before touching or rewiring hot components.")

    return {
        "risk_level": "low_voltage_lab",
        "allowed": True,
        "message": "Low-voltage educational debugging is allowed.",
        "warnings": caution
        or [
            "Do not debug live mains circuits with CircuitSage.",
            "Power off before rewiring the op-amp pins.",
        ],
    }

