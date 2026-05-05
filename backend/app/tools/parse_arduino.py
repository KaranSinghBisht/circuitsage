from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _constants(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, value in re.findall(r"(?:const\s+)?(?:int|byte)\s+(\w+)\s*=\s*([A-Za-z0-9_]+)\s*;", text):
        values[name] = value
    for name, value in re.findall(r"#define\s+(\w+)\s+([A-Za-z0-9_]+)", text):
        values[name] = value
    return values


def _resolve(token: str, constants: dict[str, str]) -> str:
    seen = set()
    current = token.strip()
    while current in constants and current not in seen:
        seen.add(current)
        current = constants[current]
    return current


def parse_arduino_text(text: str) -> dict[str, Any]:
    constants = _constants(text)
    pin_modes = [
        {"pin": _resolve(pin, constants), "mode": mode}
        for pin, mode in re.findall(r"pinMode\s*\(\s*([^,]+)\s*,\s*(INPUT_PULLUP|INPUT|OUTPUT)\s*\)", text)
    ]
    digital_writes = [
        {"pin": _resolve(pin, constants), "value": value}
        for pin, value in re.findall(r"digitalWrite\s*\(\s*([^,]+)\s*,\s*(HIGH|LOW)\s*\)", text)
    ]
    digital_reads = [_resolve(pin, constants) for pin in re.findall(r"digitalRead\s*\(\s*([^)]+)\)", text)]
    delays_ms = [int(value) for value in re.findall(r"delay\s*\(\s*(\d+)\s*\)", text)]
    serial_prints = re.findall(r"Serial\.(?:print|println)\s*\(([^)]*)\)", text)

    blink_pin = None
    for write in digital_writes:
        pin = write["pin"]
        values = {item["value"] for item in digital_writes if item["pin"] == pin}
        if {"HIGH", "LOW"} <= values and delays_ms:
            blink_pin = pin
            break

    return {
        "constants": constants,
        "pin_modes": pin_modes,
        "digital_writes": digital_writes,
        "digital_reads": digital_reads,
        "delays_ms": delays_ms,
        "serial_prints": serial_prints,
        "detected_topology": "arduino_blink" if blink_pin else "arduino_unknown",
        "blink_pin": blink_pin,
    }


def parse_arduino_file(path: str | Path) -> dict[str, Any]:
    return parse_arduino_text(Path(path).read_text(errors="ignore"))
