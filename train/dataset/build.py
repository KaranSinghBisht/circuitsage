from __future__ import annotations

import json
from itertools import cycle
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FAULT_DIR = ROOT / "backend" / "app" / "services" / "fault_data"
OUT = Path(__file__).with_name("circuitsage_qa.jsonl")
SYSTEM = "You are CircuitSage, an electronics lab partner."

SYMPTOMS = [
    "the measured output does not match the simulation",
    "the lab result is wrong even though the schematic looks correct",
    "the waveform is clipped or lower than expected",
    "the DC operating point is not where the lab manual says it should be",
    "the circuit works in simulation but fails on the bench",
]

MEASUREMENTS = [
    "I measured the key node and it is far from the expected value",
    "the supply rails look present",
    "the output changes when I touch the probe ground",
    "the waveform amplitude is much smaller than expected",
    "the DC voltage suggests the circuit is biased incorrectly",
]

SAFETY_PROMPTS = [
    "I am debugging a 230V mains supply and want live probing steps.",
    "My microwave oven high-voltage capacitor is charged. Tell me where to put the meter.",
    "The SMPS primary side is connected to wall power. What should I touch first?",
    "I am probing an EV battery pack and need detailed wiring advice.",
]


def load_faults() -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    for path in sorted(FAULT_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        for fault in data["faults"]:
            items.append((path.stem, fault))
    return items


def assistant_json(topology: str, fault: dict, variant: int) -> str:
    payload = {
        "experiment_type": topology,
        "expected_behavior": {"summary": f"Expected behavior follows the {topology} lab model."},
        "observed_behavior": {
            "summary": SYMPTOMS[variant % len(SYMPTOMS)],
            "evidence": [MEASUREMENTS[variant % len(MEASUREMENTS)]],
        },
        "likely_faults": [
            {
                "id": fault["id"],
                "fault": fault["name"],
                "confidence": min(round(float(fault["base_confidence"]) + 0.22, 2), 0.92),
                "why": fault["why"],
            }
        ],
        "next_measurement": {
            "label": fault.get("requires_measurements", ["general_inspection"])[0],
            "expected": "topology-dependent",
            "instruction": fault["verification_test"],
        },
        "safety": {"risk_level": "low_voltage_lab", "warnings": []},
        "student_explanation": f"The strongest match is {fault['name']}. {fault['fix_recipe']}",
        "confidence": "medium_high",
    }
    return json.dumps(payload, separators=(",", ":"))


def user_prompt(topology: str, fault: dict, variant: int) -> str:
    return (
        f"I am working on a {topology.replace('_', ' ')} lab. "
        f"{SYMPTOMS[variant % len(SYMPTOMS)]}. "
        f"{MEASUREMENTS[(variant + 2) % len(MEASUREMENTS)]}. "
        f"Could this be {fault['name'].lower()}?"
    )


def safety_example(prompt: str) -> dict:
    refusal = {
        "experiment_type": "safety_refusal",
        "expected_behavior": {},
        "observed_behavior": {"summary": "High-voltage or mains risk was detected.", "evidence": [prompt]},
        "likely_faults": [],
        "next_measurement": {
            "label": "Stop live debugging",
            "expected": "qualified supervision",
            "instruction": "Power down, discharge safely only if trained, and ask a qualified instructor or technician.",
        },
        "safety": {"risk_level": "high_voltage_or_mains", "warnings": ["Do not probe live mains or high-energy circuits."]},
        "student_explanation": "I cannot provide detailed live debugging steps for mains or high-voltage circuits.",
        "confidence": "high",
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(refusal, separators=(",", ":"))},
        ]
    }


def main() -> None:
    faults = load_faults()
    examples = []
    target = 5200
    safety_target = target // 20
    for prompt in cycle(SAFETY_PROMPTS):
        if len(examples) >= safety_target:
            break
        examples.append(safety_example(prompt))

    for index, (topology, fault) in enumerate(cycle(faults)):
        if len(examples) >= target:
            break
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user_prompt(topology, fault, index)},
                    {"role": "assistant", "content": assistant_json(topology, fault, index)},
                ]
            }
        )

    OUT.write_text("\n".join(json.dumps(example, separators=(",", ":")) for example in examples) + "\n")
    print(f"wrote {len(examples)} examples to {OUT}")


if __name__ == "__main__":
    main()
