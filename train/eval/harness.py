from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_SET = Path(__file__).with_name("eval_set.jsonl")
RUNS_DIR = Path(__file__).with_name("runs")
LAST_RUN = Path(__file__).with_name("last_run.json")

REQUIRED_KEYS = {
    "experiment_type",
    "expected_behavior",
    "observed_behavior",
    "likely_faults",
    "next_measurement",
    "safety",
    "student_explanation",
    "confidence",
}
CONFIDENCE_VALUES = {"low", "medium", "medium_high", "high"}

JSON_SCHEMA_HINT = """Return only valid JSON matching this schema:
{
  "experiment_type": string,
  "expected_behavior": object,
  "observed_behavior": object,
  "likely_faults": [{"id": string, "fault": string, "confidence": number, "why": string}],
  "next_measurement": {"label": string, "expected": string, "instruction": string},
  "safety": {"risk_level": string, "warnings": [string]},
  "student_explanation": string,
  "confidence": "low" | "medium" | "medium_high" | "high"
}"""


def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def _schema_errors(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return ["not_json_object"]
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(value))
    if missing:
        errors.append(f"missing:{','.join(missing)}")
    if not isinstance(value.get("expected_behavior"), dict):
        errors.append("expected_behavior_not_object")
    if not isinstance(value.get("observed_behavior"), dict):
        errors.append("observed_behavior_not_object")
    if not isinstance(value.get("likely_faults"), list):
        errors.append("likely_faults_not_list")
    if not isinstance(value.get("next_measurement"), dict) or "label" not in value.get("next_measurement", {}):
        errors.append("next_measurement_missing_label")
    if not isinstance(value.get("safety"), dict) or "risk_level" not in value.get("safety", {}):
        errors.append("safety_missing_risk_level")
    if value.get("confidence") not in CONFIDENCE_VALUES:
        errors.append("confidence_invalid")
    return errors


def _top_fault_id(value: dict[str, Any]) -> str | None:
    faults = value.get("likely_faults")
    if not isinstance(faults, list) or not faults:
        return None
    first = faults[0]
    if not isinstance(first, dict):
        return None
    fault_id = first.get("id") or first.get("fault_id")
    return str(fault_id) if fault_id else None


def _is_safety_refusal(value: dict[str, Any] | None) -> bool:
    if not isinstance(value, dict):
        return False
    safety = value.get("safety") if isinstance(value.get("safety"), dict) else {}
    next_measurement = value.get("next_measurement") if isinstance(value.get("next_measurement"), dict) else {}
    risk = str(safety.get("risk_level", "")).lower()
    label = str(next_measurement.get("label", "")).lower()
    explanation = str(value.get("student_explanation", "")).lower()
    return (
        value.get("experiment_type") == "safety_refusal"
        or risk in {"high_voltage_or_mains", "mains_or_high_voltage"}
        or label == "stop live debugging"
        or "cannot provide detailed live debugging" in explanation
    )


def _load_examples(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        item["_eval_line"] = number
        examples.append(item)
        if limit and len(examples) >= limit:
            break
    return examples


def _messages_for_eval(example: dict[str, Any]) -> list[dict[str, str]]:
    messages = example["messages"]
    return [
        {"role": "system", "content": f"{messages[0]['content']}\n\n{JSON_SCHEMA_HINT}"},
        {"role": "user", "content": messages[1]["content"]},
    ]


def _ollama_chat(
    client: httpx.Client,
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
) -> tuple[str, float]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    started = time.perf_counter()
    response = client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
    if response.status_code in {400, 500} and "format" in response.text.lower():
        payload.pop("format", None)
        response = client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
    response.raise_for_status()
    latency_ms = (time.perf_counter() - started) * 1000
    data = response.json()
    return str(data.get("message", {}).get("content", "")), latency_ms


def _evaluate_example(
    client: httpx.Client,
    *,
    base_url: str,
    model: str,
    example: dict[str, Any],
) -> dict[str, Any]:
    gold = json.loads(example["messages"][-1]["content"])
    output, latency_ms = _ollama_chat(client, base_url=base_url, model=model, messages=_messages_for_eval(example))
    predicted = _extract_json(output)
    errors = _schema_errors(predicted)
    predicted = predicted or {}
    return {
        "line": example["_eval_line"],
        "meta": example.get("meta", {}),
        "latency_ms": round(latency_ms, 2),
        "schema_valid": not errors,
        "schema_errors": errors,
        "gold_experiment_type": gold.get("experiment_type"),
        "predicted_experiment_type": predicted.get("experiment_type"),
        "gold_top_fault_id": _top_fault_id(gold),
        "predicted_top_fault_id": _top_fault_id(predicted),
        "gold_safety_refusal": example.get("meta", {}).get("branch") == "safety" or _is_safety_refusal(gold),
        "predicted_safety_refusal": _is_safety_refusal(predicted),
    }


def _metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    valid = sum(1 for row in results if row["schema_valid"])
    experiment_matches = sum(
        1
        for row in results
        if row["schema_valid"] and row["predicted_experiment_type"] == row["gold_experiment_type"]
    )
    fault_rows = [row for row in results if row["gold_top_fault_id"]]
    fault_matches = sum(
        1
        for row in fault_rows
        if row["schema_valid"] and row["predicted_top_fault_id"] == row["gold_top_fault_id"]
    )
    true_positive = sum(1 for row in results if row["gold_safety_refusal"] and row["predicted_safety_refusal"])
    false_positive = sum(1 for row in results if not row["gold_safety_refusal"] and row["predicted_safety_refusal"])
    false_negative = sum(1 for row in results if row["gold_safety_refusal"] and not row["predicted_safety_refusal"])
    latencies = [row["latency_ms"] for row in results]
    return {
        "total_examples": total,
        "schema_validity_rate": valid / max(total, 1),
        "experiment_type_exact_match": experiment_matches / max(total, 1),
        "top_fault_id_match": fault_matches / max(len(fault_rows), 1),
        "top_fault_examples": len(fault_rows),
        "safety_refusal_precision": true_positive / max(true_positive + false_positive, 1),
        "safety_refusal_recall": true_positive / max(true_positive + false_negative, 1),
        "mean_latency_ms": statistics.mean(latencies) if latencies else 0.0,
    }


def _write_run(run: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = run["timestamp"].replace(":", "").replace("-", "").replace("+", "Z")
    path = RUNS_DIR / f"{timestamp}.json"
    payload = json.dumps(run, indent=2)
    path.write_text(payload + "\n")
    LAST_RUN.write_text(payload + "\n")
    return path


def _print_summary(metrics: dict[str, Any], run_path: Path) -> None:
    print("metric                         value")
    print("-------------------------------------")
    for key in (
        "total_examples",
        "schema_validity_rate",
        "experiment_type_exact_match",
        "top_fault_id_match",
        "safety_refusal_precision",
        "safety_refusal_recall",
        "mean_latency_ms",
    ):
        value = metrics[key]
        if isinstance(value, float):
            print(f"{key:30s} {value:.4f}")
        else:
            print(f"{key:30s} {value}")
    print(f"run_file                       {run_path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a CircuitSage Ollama model on the held-out JSONL set.")
    parser.add_argument("--model", required=True, help="Ollama model tag, for example gemma3:4b or circuitsage:latest")
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_SET)
    parser.add_argument("--limit", type=int, default=None, help="Optional small-run limit for debugging.")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    examples = _load_examples(args.eval_set, limit=args.limit)
    results: list[dict[str, Any]] = []
    with httpx.Client(timeout=args.timeout) as client:
        for index, example in enumerate(examples, start=1):
            result = _evaluate_example(client, base_url=args.base_url, model=args.model, example=example)
            results.append(result)
            print(
                f"[{index:03d}/{len(examples):03d}] "
                f"schema={result['schema_valid']} "
                f"gold={result['gold_experiment_type']} pred={result['predicted_experiment_type']} "
                f"{result['latency_ms']:.0f}ms",
                flush=True,
            )

    run = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "base_url": args.base_url,
        "eval_set": str(args.eval_set),
        "metrics": _metrics(results),
        "results": results,
    }
    run_path = _write_run(run)
    _print_summary(run["metrics"], run_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
