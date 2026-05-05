from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np


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

    fft = fft_analysis(times, vout)
    return {
        "v_min": round(v_min, 3),
        "v_max": round(v_max, 3),
        "mean": round(v_mean, 3),
        "vin_peak": round(max(abs(v) for v in vin), 3),
        "vout_peak": round(max(abs(v) for v in vout), 3),
        "is_saturated": near_positive or near_negative,
        "saturation_rail": "positive" if near_positive else "negative" if near_negative else None,
        "frequency_estimate_hz": _zero_crossing_frequency(times, vout),
        "fft": fft,
    }


def fft_analysis(times: list[float], values: list[float]) -> dict[str, Any]:
    if len(times) < 8 or len(times) != len(values):
        return {"error": "not_enough_samples", "confidence": "low"}
    t = np.asarray(times, dtype=float)
    y = np.asarray(values, dtype=float)
    order = np.argsort(t)
    t = t[order]
    y = y[order] - float(np.mean(y))
    dt = float(np.median(np.diff(t)))
    if dt <= 0:
        return {"error": "invalid_timebase", "confidence": "low"}
    window = np.hanning(len(y))
    spectrum = np.fft.rfft(y * window)
    freqs = np.fft.rfftfreq(len(y), dt)
    mags = np.abs(spectrum)
    if len(mags) < 3 or float(np.max(mags[1:])) <= 1e-12:
        return {"fundamental_hz": 0.0, "top_harmonics": [], "thd_percent": 0.0, "confidence": "low"}
    fundamental_index = int(np.argmax(mags[1:]) + 1)
    fundamental = float(freqs[fundamental_index])
    fundamental_mag = float(mags[fundamental_index])
    harmonics = []
    harmonic_power = 0.0
    for n in range(2, 7):
        target = fundamental * n
        idx = int(np.argmin(np.abs(freqs - target)))
        if idx < len(mags):
            energy = float(mags[idx] / fundamental_mag)
            harmonic_power += energy * energy
            harmonics.append({"order": n, "frequency_hz": round(float(freqs[idx]), 3), "relative_energy": round(energy, 4)})
    top = sorted(harmonics, key=lambda item: item["relative_energy"], reverse=True)[:5]
    return {
        "fundamental_hz": round(fundamental, 3),
        "top_harmonics": top,
        "thd_percent": round(math.sqrt(harmonic_power) * 100, 3),
        "confidence": "high" if len(values) >= 64 else "medium",
    }


def _read_time_vout(path: str | Path) -> tuple[list[float], list[float]]:
    rows = list(csv.DictReader(Path(path).read_text().splitlines()))
    times = [float(row.get("time_s", 0) or 0) for row in rows]
    values = [float(row.get("vout_v", row.get("value", 0)) or 0) for row in rows]
    return times, values


def _flat_top_fraction(values: list[float]) -> float:
    if not values:
        return 0.0
    arr = np.asarray(values, dtype=float)
    span = float(np.max(arr) - np.min(arr))
    if span <= 0:
        return 0.0
    edge = span * 0.0005
    return float(np.mean((np.max(arr) - arr <= edge) | (arr - np.min(arr) <= edge)))


def compare_waveform_spectra(expected_csv: str | Path, observed_csv: str | Path) -> dict[str, Any]:
    expected_times, expected_values = _read_time_vout(expected_csv)
    observed_times, observed_values = _read_time_vout(observed_csv)
    expected = fft_analysis(expected_times, expected_values)
    observed = fft_analysis(observed_times, observed_values)
    expected_f = float(expected.get("fundamental_hz", 0) or 0)
    observed_f = float(observed.get("fundamental_hz", 0) or 0)
    observed_thd = float(observed.get("thd_percent", 0) or 0)
    flat_fraction = _flat_top_fraction(observed_values)
    classification = "matches_expected"
    confidence = 0.74
    if expected_f and observed_f and abs(observed_f - expected_f) / expected_f > 0.03:
        classification = "frequency_drift"
        confidence = min(0.95, abs(observed_f - expected_f) / expected_f * 10)
    if observed_f == 0 or max(abs(v) for v in observed_values or [0]) < 1e-6:
        classification = "missing_fundamental"
        confidence = 0.9
    elif flat_fraction > 0.18 and observed_thd > 8:
        classification = "clipping"
        confidence = min(0.98, 0.8 + flat_fraction)
    elif observed_thd > 7:
        classification = "harmonic_distortion"
        confidence = min(0.95, observed_thd / 30)
    elif observed_thd > 3 and np.std(observed_values) > np.std(expected_values) * 1.4:
        classification = "noise_floor_too_high"
        confidence = 0.7
    return {
        "mismatch_type": classification,
        "confidence": round(float(confidence), 3),
        "expected_fft": expected,
        "observed_fft": observed,
        "flat_top_fraction": round(flat_fraction, 4),
    }
