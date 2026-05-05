from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any


VALUE_MULTIPLIERS = {
    "": 1.0,
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "r": 1.0,
    "k": 1e3,
    "meg": 1e6,
    "g": 1e9,
    "t": 1e12,
}


def parse_spice_value(raw: str) -> float:
    text = raw.strip()
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)([a-zA-Z]*)", text, re.IGNORECASE)
    if not match:
        raise ValueError(f"Unsupported SPICE value: {raw}")
    number, suffix = match.groups()
    suffix = suffix.lower()
    if suffix not in VALUE_MULTIPLIERS:
        raise ValueError(f"Unsupported SPICE suffix: {raw}")
    return float(number) * VALUE_MULTIPLIERS[suffix]


def _norm_node(node: str) -> str:
    lowered = node.lower()
    if lowered in {"0", "gnd", "ground"}:
        return "0"
    return node


def _parse_source_value(parts: list[str]) -> dict[str, Any]:
    raw = " ".join(parts)
    result: dict[str, Any] = {"shape": raw}
    if not parts:
        return result
    if parts[0].upper() == "DC" and len(parts) >= 2:
        result["dc"] = parse_spice_value(parts[1])
    elif parts[0].upper().startswith("SIN"):
        nums = re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[a-zA-Z]+)?", raw)
        if len(nums) >= 3:
            result["offset"] = parse_spice_value(nums[0])
            result["amplitude"] = parse_spice_value(nums[1])
            result["frequency_hz"] = parse_spice_value(nums[2])
    else:
        try:
            result["dc"] = parse_spice_value(parts[0])
        except ValueError:
            pass
    return result


def _resistor_between(resistors: list[dict[str, Any]], a: str, b: str) -> dict[str, Any] | None:
    wanted = {_norm_node(a), _norm_node(b)}
    return next((r for r in resistors if {_norm_node(n) for n in r["nodes"]} == wanted), None)


def _source_between(sources: list[dict[str, Any]], a: str, b: str) -> dict[str, Any] | None:
    wanted = {_norm_node(a), _norm_node(b)}
    return next((s for s in sources if {_norm_node(n) for n in s["nodes"]} == wanted), None)


def _detect_op_amp(components: list[dict[str, Any]], sources: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    resistors = [c for c in components if c["kind"] == "resistor"]
    controlled = [c for c in components if c["kind"] in {"controlled_source", "subcircuit"}]
    if not controlled:
        return None

    output_nodes = {c["nodes"][0] for c in controlled if c["nodes"]}
    output_nodes.add("vout")
    for output in output_nodes:
        for rf in resistors:
            if output not in rf["nodes"]:
                continue
            inv = next(n for n in rf["nodes"] if n != output)
            rin = next((r for r in resistors if r is not rf and inv in r["nodes"] and "0" not in r["nodes"]), None)
            rg = next((r for r in resistors if r is not rf and inv in r["nodes"] and "0" in [_norm_node(n) for n in r["nodes"]]), None)
            if rin:
                input_node = next(n for n in rin["nodes"] if n != inv)
                if _source_between(sources, input_node, "0") or input_node.lower() in {"vin", "input"}:
                    gain = round(-(rf["value"] / rin["value"]), 3)
                    return "op_amp_inverting", {"gain": gain, "rin_ohms": rin["value"], "rf_ohms": rf["value"]}
            if rg:
                noninv_source = next((s for s in sources if inv not in s["nodes"] and "0" in [_norm_node(n) for n in s["nodes"]]), None)
                if noninv_source:
                    gain = round(1 + (rf["value"] / rg["value"]), 3)
                    return "op_amp_noninverting", {"gain": gain, "rg_ohms": rg["value"], "rf_ohms": rf["value"]}
    return None


def _detect_rc_lowpass(components: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    resistors = [c for c in components if c["kind"] == "resistor"]
    capacitors = [c for c in components if c["kind"] == "capacitor"]
    for resistor in resistors:
        for cap in capacitors:
            cap_nodes = {_norm_node(n) for n in cap["nodes"]}
            if "0" not in cap_nodes:
                continue
            output_node = next(n for n in cap["nodes"] if _norm_node(n) != "0")
            if output_node in resistor["nodes"]:
                fc = 1 / (2 * math.pi * resistor["value"] * cap["value"])
                return "rc_lowpass", {
                    "cutoff_hz": round(fc, 3),
                    "resistance_ohms": resistor["value"],
                    "capacitance_f": cap["value"],
                }
    return None


def _detect_voltage_divider(components: list[dict[str, Any]], sources: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    resistors = [c for c in components if c["kind"] == "resistor"]
    for source in sources:
        source_nodes = [_norm_node(n) for n in source["nodes"]]
        if "0" not in source_nodes:
            continue
        high_node = next(n for n in source["nodes"] if _norm_node(n) != "0")
        for r1 in resistors:
            if high_node not in r1["nodes"]:
                continue
            tap = next(n for n in r1["nodes"] if n != high_node)
            r2 = _resistor_between(resistors, tap, "0")
            if r2:
                vin = source.get("dc", source.get("amplitude"))
                computed = {
                    "r1_ohms": r1["value"],
                    "r2_ohms": r2["value"],
                    "ratio": round(r2["value"] / (r1["value"] + r2["value"]), 4),
                    "output_node": tap,
                }
                if isinstance(vin, int | float):
                    computed["vout_dc"] = round(vin * computed["ratio"], 4)
                return "voltage_divider", computed
    return None


def _detect_bjt_common_emitter(components: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    transistors = [c for c in components if c["kind"] == "bjt"]
    resistors = [c for c in components if c["kind"] == "resistor"]
    for transistor in transistors:
        collector, base, emitter = transistor["nodes"][:3]
        collector_resistor = next((r for r in resistors if collector in r["nodes"] and any(n.lower() in {"vcc", "vdd"} for n in r["nodes"])), None)
        emitter_resistor = _resistor_between(resistors, emitter, "0")
        base_bias = [r for r in resistors if base in r["nodes"]]
        if collector_resistor and emitter_resistor and len(base_bias) >= 1:
            return "bjt_common_emitter", {
                "collector_resistor_ohms": collector_resistor["value"],
                "emitter_resistor_ohms": emitter_resistor["value"],
                "base_bias_resistors": len(base_bias),
            }
    return None


def _detect_full_wave_rectifier(components: list[dict[str, Any]], sources: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    diodes = [c for c in components if c["kind"] == "diode"]
    if len(diodes) < 4:
        return None
    vin_peak = next((s.get("amplitude") for s in sources if s.get("amplitude")), None)
    computed: dict[str, Any] = {"diode_count": len(diodes), "diode_drop_v": 0.7}
    if isinstance(vin_peak, int | float):
        computed["vout_peak_estimate"] = round(max(vin_peak - 1.4, 0), 3)
    return "full_wave_rectifier", computed


def _detect_timer_555(components: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    if any("555" in c.get("subckt", "").lower() or "555" in c.get("model", "").lower() for c in components):
        resistors = [c for c in components if c["kind"] == "resistor"]
        capacitors = [c for c in components if c["kind"] == "capacitor"]
        return "timer_555_astable", {"resistor_count": len(resistors), "capacitor_count": len(capacitors)}
    return None


def _detect_nmos_low_side(components: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    for mosfet in [c for c in components if c["kind"] == "mosfet"]:
        drain, gate, source, _body = mosfet["nodes"][:4]
        if _norm_node(source) == "0":
            return "nmos_low_side_switch", {"drain_node": drain, "gate_node": gate, "source_node": source}
    return None


def _detect_instrumentation_amp(components: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    opamps = [c for c in components if c["kind"] in {"controlled_source", "subcircuit"}]
    resistors = [c for c in components if c["kind"] == "resistor"]
    if len(opamps) >= 3 and len(resistors) >= 5:
        return "instrumentation_amplifier", {"op_amp_count": len(opamps), "resistor_count": len(resistors)}
    return None


def _detect_special_op_amp_filters(components: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    controlled = [c for c in components if c["kind"] in {"controlled_source", "subcircuit"}]
    if not controlled:
        return None
    resistors = [c for c in components if c["kind"] == "resistor"]
    capacitors = [c for c in components if c["kind"] == "capacitor"]
    output_nodes = {c["nodes"][0] for c in controlled if c["nodes"]}
    output_nodes.add("vout")
    for output in output_nodes:
        for cap in capacitors:
            if output in cap["nodes"]:
                inv = next(n for n in cap["nodes"] if n != output)
                if any(inv in r["nodes"] and "vin" in [n.lower() for n in r["nodes"]] for r in resistors):
                    return "op_amp_integrator", {"feedback_capacitance_f": cap["value"]}
        for resistor in resistors:
            if output in resistor["nodes"]:
                inv = next(n for n in resistor["nodes"] if n != output)
                input_cap = next((c for c in capacitors if inv in c["nodes"] and "vin" in [n.lower() for n in c["nodes"]]), None)
                if input_cap:
                    if any(inv in r["nodes"] and "0" in [_norm_node(n) for n in r["nodes"]] for r in resistors if r is not resistor):
                        return "active_highpass_filter", {"input_capacitance_f": input_cap["value"], "feedback_resistance_ohms": resistor["value"]}
                    return "op_amp_differentiator", {"input_capacitance_f": input_cap["value"], "feedback_resistance_ohms": resistor["value"]}
                noninv_feedback = any(
                    output in r["nodes"] and any(n.lower() in {"n_noninv", "noninv", "vp"} for n in r["nodes"])
                    for r in resistors
                )
                if noninv_feedback:
                    return "schmitt_trigger", {"feedback_resistance_ohms": resistor["value"]}
    return None


def _detect_topology(components: list[dict[str, Any]], sources: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    for detector in (
        lambda: _detect_timer_555(components),
        lambda: _detect_nmos_low_side(components),
        lambda: _detect_instrumentation_amp(components),
        lambda: _detect_special_op_amp_filters(components),
        lambda: _detect_op_amp(components, sources),
        lambda: _detect_rc_lowpass(components),
        lambda: _detect_bjt_common_emitter(components),
        lambda: _detect_voltage_divider(components, sources),
        lambda: _detect_full_wave_rectifier(components, sources),
    ):
        result = detector()
        if result:
            return result
    return "unknown", {}


def parse_netlist_text(text: str) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    directives: list[str] = []
    node_set: set[str] = set()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith(";"):
            continue
        if stripped.startswith("."):
            directives.append(stripped)
            continue
        parts = stripped.split()
        if not parts:
            continue
        ref = parts[0]
        designator = ref[0].upper()

        try:
            if designator == "R" and len(parts) >= 4:
                value = parse_spice_value(parts[3])
                component = {
                    "ref": ref,
                    "kind": "resistor",
                    "nodes": [_norm_node(parts[1]), _norm_node(parts[2])],
                    "value": value,
                    "value_ohms": value,
                    "raw_value": parts[3],
                }
                components.append(component)
            elif designator == "C" and len(parts) >= 4:
                value = parse_spice_value(parts[3])
                components.append(
                    {
                        "ref": ref,
                        "kind": "capacitor",
                        "nodes": [_norm_node(parts[1]), _norm_node(parts[2])],
                        "value": value,
                        "value_f": value,
                        "raw_value": parts[3],
                    }
                )
            elif designator == "L" and len(parts) >= 4:
                value = parse_spice_value(parts[3])
                components.append(
                    {
                        "ref": ref,
                        "kind": "inductor",
                        "nodes": [_norm_node(parts[1]), _norm_node(parts[2])],
                        "value": value,
                        "value_h": value,
                        "raw_value": parts[3],
                    }
                )
            elif designator in {"V", "I"} and len(parts) >= 4:
                source = {
                    "ref": ref,
                    "kind": "voltage_source" if designator == "V" else "current_source",
                    "nodes": [_norm_node(parts[1]), _norm_node(parts[2])],
                    **_parse_source_value(parts[3:]),
                }
                sources.append(source)
                components.append(source)
            elif designator == "D" and len(parts) >= 4:
                components.append(
                    {
                        "ref": ref,
                        "kind": "diode",
                        "nodes": [_norm_node(parts[1]), _norm_node(parts[2])],
                        "model": parts[3],
                    }
                )
            elif designator == "Q" and len(parts) >= 5:
                components.append(
                    {
                        "ref": ref,
                        "kind": "bjt",
                        "nodes": [_norm_node(parts[1]), _norm_node(parts[2]), _norm_node(parts[3])],
                        "model": parts[4],
                    }
                )
            elif designator == "M" and len(parts) >= 6:
                components.append(
                    {
                        "ref": ref,
                        "kind": "mosfet",
                        "nodes": [_norm_node(parts[1]), _norm_node(parts[2]), _norm_node(parts[3]), _norm_node(parts[4])],
                        "model": parts[5],
                    }
                )
            elif designator == "X" and len(parts) >= 4:
                components.append(
                    {
                        "ref": ref,
                        "kind": "subcircuit",
                        "nodes": [_norm_node(n) for n in parts[1:-1]],
                        "subckt": parts[-1],
                    }
                )
            elif designator == "E" and len(parts) >= 6:
                components.append(
                    {
                        "ref": ref,
                        "kind": "controlled_source",
                        "nodes": [_norm_node(n) for n in parts[1:5]],
                        "gain": parse_spice_value(parts[5]),
                    }
                )
        except ValueError:
            continue

    for component in components:
        for node in component.get("nodes", []):
            node_set.add(_norm_node(node))

    detected_topology, computed = _detect_topology(components, sources)

    return {
        "components": components,
        "nodes": sorted(node_set),
        "sources": sources,
        "directives": directives,
        "detected_topology": detected_topology,
        "computed": computed,
    }


def parse_netlist_file(path: str | Path) -> dict[str, Any]:
    return parse_netlist_text(Path(path).read_text(errors="ignore"))
