from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import pstdev
from time import time
from typing import Any


@dataclass
class StreamSample:
    ts: float
    label: str
    value: float
    unit: str = "V"


WINDOWS: dict[str, dict[str, deque[StreamSample]]] = defaultdict(lambda: defaultdict(deque))
MAX_AGE_S = 60.0


def add_sample(session_id: str, label: str, value: float, unit: str = "V", ts: float | None = None) -> dict[str, Any]:
    sample = StreamSample(ts=ts or time(), label=label, value=float(value), unit=unit)
    bucket = WINDOWS[session_id][label]
    bucket.append(sample)
    cutoff = sample.ts - MAX_AGE_S
    while bucket and bucket[0].ts < cutoff:
        bucket.popleft()
    return {"accepted": True, "sample": sample.__dict__, "drift": drift_for_label(session_id, label)}


def drift_for_label(session_id: str, label: str, horizon_s: float = 10.0) -> dict[str, Any] | None:
    now = time()
    values = [sample.value for sample in WINDOWS[session_id][label] if sample.ts >= now - horizon_s]
    if len(values) < 8:
        return None
    sigma = pstdev(values)
    expected_sigma = 0.15 if label.lower() in {"vout", "output", "loaded_vout"} else 0.08
    if sigma > expected_sigma:
        return {
            "type": "drift",
            "label": label,
            "stddev": round(sigma, 4),
            "expected_stddev": expected_sigma,
            "message": f"{label} is drifting/intermittent over the last {int(horizon_s)} s.",
        }
    return None


def snapshot(session_id: str) -> dict[str, Any]:
    labels = {}
    events = []
    for label, samples in WINDOWS.get(session_id, {}).items():
        labels[label] = [{"ts": sample.ts, "value": sample.value, "unit": sample.unit} for sample in samples]
        drift = drift_for_label(session_id, label)
        if drift:
            events.append(drift)
    return {"session_id": session_id, "labels": labels, "events": events}
