from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from itertools import cycle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from augment import paraphrase  # noqa: E402
from templates import TEMPLATES, Template, render  # noqa: E402


FAULT_DIR = ROOT / "backend" / "app" / "services" / "fault_data"
OUT = Path(__file__).with_name("circuitsage_qa.jsonl")
SYSTEM = "You are CircuitSage, an electronics lab partner."
TARGET = 6000
SAFETY_TARGET = 300
NEGATIVE_TARGET = 360

SAFETY_PROMPTS = [
    "I am debugging a 230V mains supply and want live probing steps.",
    "My microwave oven high-voltage capacitor is charged. Tell me where to put the meter.",
    "The SMPS primary side is connected to wall power. What should I touch first?",
    "I am probing an EV battery pack and need detailed wiring advice.",
    "The wall outlet keeps tripping; give me detailed steps to test it live.",
]


def load_faults() -> dict[str, dict[str, dict]]:
    fault_map: dict[str, dict[str, dict]] = {}
    for path in sorted(FAULT_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        fault_map[path.stem] = {fault["id"]: fault for fault in data["faults"]}
    return fault_map


FAULTS = load_faults()


def assistant_json(template: Template, fills: dict, seed: int) -> str:
    if template.fault_id is None:
        payload = {
            "experiment_type": template.topology,
            "expected_behavior": {"summary": f"Expected behavior depends on the {template.topology} topology and component values."},
            "observed_behavior": {"summary": fills["observed"], "evidence": ["No decisive measurement was provided."]},
            "likely_faults": [],
            "next_measurement": {
                "label": template.expected_label or "document_expected_vs_observed_node",
                "expected": "one measured node tied to a circuit reference",
                "instruction": "Measure the output, input/reference node, and supply or bias node before naming a component fault.",
            },
            "safety": {"risk_level": "low_voltage_lab", "warnings": []},
            "student_explanation": "There is not enough bench evidence to rank a specific fault yet. Start with one expected-versus-observed node measurement.",
            "confidence": "low",
        }
        return json.dumps(payload, separators=(",", ":"))

    fault = FAULTS[template.topology][template.fault_id]
    confidence = min(round(float(fault["base_confidence"]) + 0.18 + (seed % 7) * 0.01, 2), 0.92)
    payload = {
        "experiment_type": template.topology,
        "expected_behavior": {
            "summary": f"Expected {template.topology.replace('_', ' ')} behavior with {fills['amp']} input at {fills['f']}.",
            "rails": fills["rail"],
            "input_amplitude": fills["amp"],
        },
        "observed_behavior": {
            "summary": fills["observed"],
            "evidence": [f"student context: {fills['persona']}", f"frequency: {fills['f']}"],
        },
        "likely_faults": [
            {
                "id": fault["id"],
                "fault": fault["name"],
                "confidence": confidence,
                "why": fault["why"],
            }
        ],
        "next_measurement": {
            "label": template.expected_label or fault.get("requires_measurements", ["general_inspection"])[0],
            "expected": "topology-dependent",
            "instruction": fault["verification_test"],
        },
        "safety": {"risk_level": "low_voltage_lab", "warnings": []},
        "student_explanation": f"The strongest match is {fault['name']}. {fault['fix_recipe']}",
        "confidence": "medium_high" if confidence < 0.85 else "high",
    }
    return json.dumps(payload, separators=(",", ":"))


def row(prompt: str, assistant: str, meta: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant},
        ],
        "meta": meta,
    }


def variants_for(prompt: str) -> list[dict[str, str]]:
    return [{"text": prompt, "source": "original"}, *paraphrase(prompt, n=4)]


def build_branch(templates: list[Template], target: int, branch: str, start_seed: int = 0) -> list[dict]:
    examples: list[dict] = []
    seed = start_seed
    for template in cycle(templates):
        prompt, fills = render(template, seed)
        assistant = assistant_json(template, fills, seed)
        for variant in variants_for(prompt):
            examples.append(
                row(
                    variant["text"],
                    assistant,
                    {
                        "topology": template.topology,
                        "fault_id": template.fault_id,
                        "branch": branch,
                        "paraphrase_source": variant["source"],
                    },
                )
            )
            if len(examples) >= target:
                return examples
        seed += 1
    return examples


def safety_rows(target: int) -> list[dict]:
    examples: list[dict] = []
    for index in range(target):
        prompt = f"{SAFETY_PROMPTS[index % len(SAFETY_PROMPTS)]} Context number {index}: I need exact probing instructions."
        refusal = {
            "experiment_type": "safety_refusal",
            "expected_behavior": {},
            "observed_behavior": {"summary": "High-voltage or mains risk was detected.", "evidence": [prompt]},
            "likely_faults": [],
            "next_measurement": {
                "label": "Stop live debugging",
                "expected": "qualified supervision",
                "instruction": "Power down and ask a qualified instructor or technician.",
            },
            "safety": {"risk_level": "high_voltage_or_mains", "warnings": ["Do not probe live mains or high-energy circuits."]},
            "student_explanation": "I cannot provide detailed live debugging steps for mains or high-voltage circuits.",
            "confidence": "high",
        }
        examples.append(
            row(
                prompt,
                json.dumps(refusal, separators=(",", ":")),
                {"topology": "safety_refusal", "fault_id": None, "branch": "safety", "paraphrase_source": "safety_template"},
            )
        )
    return examples


def main() -> None:
    positives_by_topology: dict[str, list[Template]] = defaultdict(list)
    negatives: list[Template] = []
    for template in TEMPLATES:
        if template.fault_id is None:
            negatives.append(template)
        else:
            positives_by_topology[template.topology].append(template)

    regular_target = TARGET - SAFETY_TARGET - NEGATIVE_TARGET
    per_topology = regular_target // len(positives_by_topology)
    examples: list[dict] = []
    seed_offset = 0
    for topology in sorted(positives_by_topology):
        examples.extend(build_branch(positives_by_topology[topology], per_topology, "fault", seed_offset))
        seed_offset += 10_000
    while len(examples) < regular_target:
        topology = sorted(positives_by_topology)[len(examples) % len(positives_by_topology)]
        examples.extend(build_branch(positives_by_topology[topology], 1, "fault", seed_offset))
        seed_offset += 1

    examples.extend(build_branch(negatives, NEGATIVE_TARGET, "negative", 50_000))
    examples.extend(safety_rows(SAFETY_TARGET))
    rng = random.Random(20260505)
    rng.shuffle(examples)
    OUT.write_text("\n".join(json.dumps(example, separators=(",", ":")) for example in examples[:TARGET]) + "\n")
    print(f"wrote {len(examples[:TARGET])} examples to {OUT}")


if __name__ == "__main__":
    main()
