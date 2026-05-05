#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request


def post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.loads(response.read().decode())


def value(pattern: str, index: int) -> float:
    base = math.sin(index / 4) * 0.05
    if pattern == "intermittent" and index % 13 in {0, 1, 2}:
        return 2.0 + base
    if pattern == "drift":
        return base + index * 0.015
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--session", required=True)
    parser.add_argument("--label", default="Vout")
    parser.add_argument("--pattern", choices=["stable", "intermittent", "drift"], default="intermittent")
    parser.add_argument("--count", type=int, default=40)
    args = parser.parse_args()
    url = f"{args.base.rstrip('/')}/api/sessions/{args.session}/measurements/stream"
    for index in range(args.count):
        result = post(url, {"label": args.label, "value": value(args.pattern, index), "unit": "V"})
        print(json.dumps({"index": index, "drift": result.get("drift")}, sort_keys=True))
        time.sleep(0.2)


if __name__ == "__main__":
    main()
