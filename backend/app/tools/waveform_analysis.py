from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from typing import Any


def _zero_crossing_frequency(times: list[float], values: list[float]) -> float | None:
    crossings = []
    for i in range(1, len(values)):
        if values[i - 1] <= 0 < values[i] or values[i - 1] >= 0 > values[i]:
            crossings.append(times[i])
    if len(crossings) < 3:
        return None
    half_periods = [b - a for a, b in zip(crossings, crossings[1:]) if b > a]
    if not half_periods:
        return None
    period = 2 * mean(half_periods)
    return round(1 / period, 1) if period else None


def analyze_waveform_csv(path: str | Path) -> dict[str, Any]:
    rows = list(csv.DictReader(Path(path).read_text().splitlines()))
    if not rows:
        return {"error": "empty_csv", "is_saturated": False}

    times = [float(row.get("time_s", 0) or 0) for row in rows]
    vin = [float(row.get("vin_v", 0) or 0) for row in rows]
    vout = [float(row.get("vout_v", 0) or 0) for row in rows]

    v_min = min(vout)
    v_max = max(vout)
    v_mean = mean(vout)
    span = v_max - v_min
    near_positive = v_mean > 9 and span < 1.5
    near_negative = v_mean < -9 and span < 1.5

    return {
        "v_min": round(v_min, 3),
        "v_max": round(v_max, 3),
        "mean": round(v_mean, 3),
        "vin_peak": round(max(abs(v) for v in vin), 3),
        "vout_peak": round(max(abs(v) for v in vout), 3),
        "is_saturated": near_positive or near_negative,
        "saturation_rail": "positive" if near_positive else "negative" if near_negative else None,
        "frequency_estimate_hz": _zero_crossing_frequency(times, vout),
    }

