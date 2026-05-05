from __future__ import annotations

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


def validate_line(line: str, number: int) -> None:
    item = json.loads(line)
    messages = item["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "assistant"], number
    assistant = json.loads(messages[-1]["content"])
    missing = REQUIRED - set(assistant)
    assert not missing, (number, missing)
    assert isinstance(assistant["likely_faults"], list), number
    assert "risk_level" in assistant["safety"], number
    assert "label" in assistant["next_measurement"], number


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("circuitsage_qa.jsonl")
    count = 0
    for count, line in enumerate(path.read_text().splitlines(), start=1):
        validate_line(line, count)
    assert count >= 5000, f"expected at least 5000 lines, got {count}"
    print(f"validated {count} examples")


if __name__ == "__main__":
    main()
