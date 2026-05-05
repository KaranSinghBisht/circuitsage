from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


_OLLAMA_DISABLED = False


def _ollama_paraphrases(prompt: str, n: int) -> list[str]:
    global _OLLAMA_DISABLED
    if _OLLAMA_DISABLED:
        raise RuntimeError("ollama disabled after earlier failure")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    body = json.dumps(
        {
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "You are paraphrasing a student's circuit-debugging question.\n"
                        f"Rewrite the question {n} different ways.\n"
                        "Keep the technical content identical: same topology, same numeric values, same symptom.\n"
                        "Vary tone, length, and word order.\n"
                        "Return JSON: {\"paraphrases\": [\"...\", \"...\"]}.\n\n"
                        f"Original: {prompt}\n"
                        f"N: {n}"
                    ),
                }
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read())
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        _OLLAMA_DISABLED = True
        raise RuntimeError("ollama unavailable") from exc
    content = data.get("message", {}).get("content", "{}")
    parsed = json.loads(content)
    return [str(item) for item in parsed.get("paraphrases", [])[:n] if str(item).strip()]


def _rule_paraphrases(prompt: str, n: int) -> list[str]:
    swaps = [
        ("what should I check next", "what is the next thing to measure"),
        ("the output", "my output node"),
        ("bench", "real circuit"),
        ("debugging", "trying to debug"),
        ("measured behavior", "observed behavior"),
        ("could this be", "is it possible this is"),
    ]
    variants: list[str] = []
    for index in range(min(n, 2)):
        variant = prompt
        for old, new in swaps[index::2]:
            variant = re.sub(old, new, variant, flags=re.IGNORECASE)
        if "," in variant:
            head, tail = variant.split(",", 1)
            variant = f"{tail.strip()} In context: {head.strip()}."
        variants.append(variant)
    return variants


def paraphrase(prompt: str, n: int = 4) -> list[dict[str, str]]:
    try:
        variants = _ollama_paraphrases(prompt, n)
        if variants:
            return [{"text": text, "source": "ollama"} for text in variants]
    except Exception:
        pass
    return [{"text": text, "source": "rule"} for text in _rule_paraphrases(prompt, n)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="source", required=True)
    parser.add_argument("--out", dest="output", required=True)
    parser.add_argument("--variants", type=int, default=5)
    args = parser.parse_args()

    rows = []
    for line in Path(args.source).read_text().splitlines():
        item = json.loads(line)
        prompt = item["messages"][1]["content"]
        rows.append(item)
        for variant in paraphrase(prompt, args.variants):
            clone: dict[str, Any] = json.loads(json.dumps(item))
            clone["messages"][1]["content"] = variant["text"]
            clone.setdefault("meta", {})["paraphrase_source"] = variant["source"]
            rows.append(clone)
    Path(args.output).write_text("\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n")
    print(json.dumps({"wrote": len(rows), "out": args.output}))


if __name__ == "__main__":
    main()
