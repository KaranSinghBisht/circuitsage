from __future__ import annotations

import threading
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


# Process-global rolling window per (session, label). Mutated by both
# /api/sessions/{id}/measurements/stream POSTs and /api/sessions/{id}/stream
# GETs that hit it concurrently — must be guarded.
WINDOWS: dict[str, dict[str, deque[StreamSample]]] = defaultdict(lambda: defaultdict(deque))
SESSION_LAST_SEEN: dict[str, float] = {}
_LOCK = threading.Lock()
MAX_AGE_S = 60.0
SESSION_IDLE_TTL_S = 3600.0  # evict whole-session buckets after 1 hour idle


def _evict_idle_locked(now: float) -> None:
    """Drop windows for sessions that haven't received samples in SESSION_IDLE_TTL_S.
    Caller must hold _LOCK."""
    stale = [
        sid
        for sid, last in SESSION_LAST_SEEN.items()
        if now - last > SESSION_IDLE_TTL_S
    ]
    for sid in stale:
        WINDOWS.pop(sid, None)
        SESSION_LAST_SEEN.pop(sid, None)


def add_sample(session_id: str, label: str, value: float, unit: str = "V", ts: float | None = None) -> dict[str, Any]:
    sample = StreamSample(ts=ts or time(), label=label, value=float(value), unit=unit)
    with _LOCK:
        _evict_idle_locked(sample.ts)
        bucket = WINDOWS[session_id][label]
        bucket.append(sample)
        cutoff = sample.ts - MAX_AGE_S
        while bucket and bucket[0].ts < cutoff:
            bucket.popleft()
        SESSION_LAST_SEEN[session_id] = sample.ts
        drift = _drift_for_label_locked(session_id, label)
    return {"accepted": True, "sample": sample.__dict__, "drift": drift}


def _drift_for_label_locked(session_id: str, label: str, horizon_s: float = 10.0) -> dict[str, Any] | None:
    """Caller must hold _LOCK. Snapshots a list of values from the bucket so
    later analysis works on an immutable copy."""
    now = time()
    bucket = WINDOWS.get(session_id, {}).get(label)
    if not bucket:
        return None
    values = [sample.value for sample in bucket if sample.ts >= now - horizon_s]
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


def drift_for_label(session_id: str, label: str, horizon_s: float = 10.0) -> dict[str, Any] | None:
    with _LOCK:
        return _drift_for_label_locked(session_id, label, horizon_s=horizon_s)


def snapshot(session_id: str) -> dict[str, Any]:
    labels: dict[str, list[dict[str, Any]]] = {}
    events: list[dict[str, Any]] = []
    with _LOCK:
        # Snapshot bucket contents into plain lists under the lock so the
        # caller iterates a safe immutable copy after the lock releases.
        for label, samples in WINDOWS.get(session_id, {}).items():
            labels[label] = [
                {"ts": sample.ts, "value": sample.value, "unit": sample.unit}
                for sample in samples
            ]
            drift = _drift_for_label_locked(session_id, label)
            if drift:
                events.append(drift)
    return {"session_id": session_id, "labels": labels, "events": events}
