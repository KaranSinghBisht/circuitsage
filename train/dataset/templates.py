from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any


@dataclass(frozen=True)
class Template:
    topology: str
    fault_id: str | None
    persona: str
    template: str
    expected_label: str | None


RAILS = ["+/-5 V", "+/-9 V", "+/-12 V", "+/-15 V"]
FREQUENCIES = ["10 Hz", "1 kHz", "10 kHz", "100 kHz"]
AMPLITUDES = ["10 mV peak", "100 mV peak", "1 V peak", "5 V peak"]
RESISTORS = ["1 kOhm", "4.7 kOhm", "10 kOhm", "47 kOhm", "100 kOhm"]
CAPACITORS = ["1 nF", "10 nF", "100 nF", "1 uF", "10 uF"]
OBSERVED = ["stuck high", "much smaller than expected", "clipped", "near ground", "not changing"]

PERSONAS = ["first-year EEE", "polytechnic", "self-taught maker", "MSc lab tutor"]

QUESTION_STYLES = [
    "what should I check next?",
    "is {cause} the cause?",
    "I tried checking power, now what?",
    "explain why my circuit does this.",
    "compare expected to observed and tell me the next measurement.",
    "which node should I measure before changing parts?",
    "could this be a wiring issue?",
    "what evidence would confirm the fault?",
    "how do I separate a bad value from a bad connection?",
    "what is the fastest safe debug step?",
]

TOPOLOGY_FAULTS = {
    "op_amp_inverting": [
        ("floating_noninv_input", "V_noninv", "floating reference input"),
        ("missing_feedback", "feedback_continuity", "open feedback path"),
        ("rail_imbalance", "v_supply_pos", "rail or ground problem"),
    ],
    "op_amp_noninverting": [
        ("rg_open", "rg_continuity", "open gain resistor"),
        ("feedback_wrong_value", "rf_value", "wrong feedback value"),
        ("input_reference_missing", "source_ground_continuity", "missing input reference"),
    ],
    "rc_lowpass": [
        ("wrong_capacitor_value", "capacitance_value", "wrong capacitor value"),
        ("input_output_swapped", "node_probe_location", "swapped input and output"),
        ("capacitor_ground_open", "capacitor_ground_continuity", "open capacitor ground"),
    ],
    "voltage_divider": [
        ("load_resistance_too_low", "loaded_vout", "load pulling the divider down"),
        ("wrong_resistor_value", "r1_value", "wrong resistor value"),
        ("divider_ground_open", "r2_ground_continuity", "open lower resistor ground"),
    ],
    "bjt_common_emitter": [
        ("incorrect_base_bias", "collector_voltage", "base bias saturation"),
        ("emitter_resistor_open", "emitter_voltage", "open emitter path"),
        ("collector_load_open", "collector_resistor_continuity", "open collector load"),
    ],
    "full_wave_rectifier": [
        ("diode_reversed", "diode_orientation", "reversed bridge diode"),
        ("missing_bridge_ground", "bridge_ground_continuity", "floating bridge return"),
        ("load_too_heavy", "load_resistance", "load too heavy"),
    ],
}

BASE_PHRASES = [
    "I built a {topology} lab on {rail} rails with {amp} input at {f}; the output is {observed},",
    "As a {persona} student, my {topology} setup uses {rin} and {rf}; the bench reading is {observed},",
    "My simulator says the {topology} should behave normally at {f}, but the real circuit is {observed},",
    "I swapped probes twice on this {topology}; with {amp} input, Vout is {observed},",
    "During the {topology} checkout, the manual expectation and the observed value disagree: it is {observed},",
    "The {topology} works in SPICE, but on the breadboard it is {observed} with {rail} rails,",
    "I am debugging a {topology}; after measuring the obvious supply nodes the output remains {observed},",
    "For my {topology}, changing frequency to {f} still leaves the symptom {observed},",
    "The expected result for this {topology} is not showing up; I see {observed} at the output,",
    "I have a {topology} with {rin}/{rf} values and the measured behavior is {observed},",
]


def _make_templates() -> list[Template]:
    templates: list[Template] = []
    for topology, faults in TOPOLOGY_FAULTS.items():
        count = 0
        for fault_id, expected_label, cause in faults:
            for phrase in BASE_PHRASES:
                style = QUESTION_STYLES[count % len(QUESTION_STYLES)].format(cause=cause)
                persona = PERSONAS[count % len(PERSONAS)]
                templates.append(
                    Template(
                        topology=topology,
                        fault_id=fault_id,
                        persona=persona,
                        template=f"{phrase} {style}",
                        expected_label=expected_label,
                    )
                )
                count += 1
        for index in range(4):
            persona = PERSONAS[(count + index) % len(PERSONAS)]
            templates.append(
                Template(
                    topology=topology,
                    fault_id=None,
                    persona=persona,
                    template=(
                        "I have a {topology} from the lab manual, but I only know that something is {observed}. "
                        "I have not measured the key nodes yet; what evidence do you need?"
                    ),
                    expected_label=None,
                )
            )
    return templates


TEMPLATES = _make_templates()


def render(template: Template, seed: int) -> tuple[str, dict[str, Any]]:
    rng = random.Random(seed)
    values = {
        "topology": template.topology.replace("_", " "),
        "persona": template.persona,
        "rail": rng.choice(RAILS),
        "f": rng.choice(FREQUENCIES),
        "amp": rng.choice(AMPLITUDES),
        "rin": rng.choice(RESISTORS),
        "rf": rng.choice(RESISTORS),
        "cap": rng.choice(CAPACITORS),
        "observed": rng.choice(OBSERVED),
    }
    prompt = (
        template.template.format(**values)
        + f" Setup details: rails {values['rail']}, input {values['amp']}, frequency {values['f']}, R {values['rin']}, C {values['cap']}."
    )
    return prompt, values
