from __future__ import annotations

from collections import Counter
import json
import sys
from pathlib import Path


REQUIRED = {
    "experiment_type",
    "expected_behavior",
    "observed_behavior",
    "likely_faults",
    "next_measurement",
    "safety",
    "student_explanation",
    "confidence",
}


def validate_line(line: str, number: int) -> tuple[str, str, str]:
    item = json.loads(line)
    messages = item["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "assistant"], number
    assistant = json.loads(messages[-1]["content"])
    missing = REQUIRED - set(assistant)
    assert not missing, (number, missing)
    assert isinstance(assistant["likely_faults"], list), number
    assert "risk_level" in assistant["safety"], number
    assert "label" in assistant["next_measurement"], number
    topology = assistant["experiment_type"]
    branch = item.get("meta", {}).get("branch", "unknown")
    source = item.get("meta", {}).get("paraphrase_source", "unknown")
    return topology, branch, source


def pct(count: int, total: int) -> float:
    return count / max(total, 1)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("circuitsage_qa.jsonl")
    lines = path.read_text().splitlines()
    prompts = []
    topologies: Counter[str] = Counter()
    branches: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for number, line in enumerate(lines, start=1):
        topology, branch, source = validate_line(line, number)
        item = json.loads(line)
        prompts.append(item["messages"][1]["content"])
        topologies[topology] += 1
        branches[branch] += 1
        sources[source] += 1

    total = len(lines)
    unique_prompts = len(set(prompts))
    dupes = Counter(prompts)
    max_dupe = max(dupes.values()) if dupes else 0
    safety_ratio = pct(branches["safety"], total)
    negative_ratio = pct(branches["negative"], total)

    assert 5000 <= total <= 8000, f"line count out of range: {total}"
    assert unique_prompts >= 1500, f"unique prompts too low: {unique_prompts}"
    assert 0.04 <= safety_ratio <= 0.06, f"safety ratio out of range: {safety_ratio:.3f}"
    assert 0.04 <= negative_ratio <= 0.10, f"negative ratio out of range: {negative_ratio:.3f}"
    assert max_dupe <= 8, f"user prompt duplicated too many times: {max_dupe}"

    non_safety_total = total - branches["safety"]
    for topology, count in topologies.items():
        if topology == "safety_refusal":
            continue
        ratio = pct(count, non_safety_total)
        assert 0.10 <= ratio <= 0.30, f"{topology} distribution out of range: {ratio:.3f}"

    print("topology distribution")
    for topology, count in sorted(topologies.items()):
        print(f"{topology:24s} {count:5d} {pct(count, total):.3f}")
    print("branch distribution")
    for branch, count in sorted(branches.items()):
        print(f"{branch:24s} {count:5d} {pct(count, total):.3f}")
    print("paraphrase sources")
    for source, count in sorted(sources.items()):
        print(f"{source:24s} {count:5d} {pct(count, total):.3f}")
    print(f"unique_user_prompts {unique_prompts}")
    print(f"max_prompt_dupes {max_dupe}")


if __name__ == "__main__":
    main()
