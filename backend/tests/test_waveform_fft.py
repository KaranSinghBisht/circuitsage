from __future__ import annotations

import csv
import math
from pathlib import Path

from app.tools.waveform_analysis import compare_waveform_spectra, fft_analysis


def _write(path: Path, freq: float, transform=None) -> None:
    rows = []
    for index in range(5000):
        t = index / 100_000
        value = math.sin(2 * math.pi * freq * t)
        if transform:
            value = transform(t, value)
        rows.append({"time_s": t, "vout_v": value})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_s", "vout_v"])
        writer.writeheader()
        writer.writerows(rows)


def test_fft_analysis_reports_fundamental_and_harmonics() -> None:
    times = [index / 100_000 for index in range(1000)]
    values = [math.sin(2 * math.pi * 1000 * t) + 0.1 * math.sin(2 * math.pi * 3000 * t) for t in times]
    result = fft_analysis(times, values)
    assert abs(result["fundamental_hz"] - 1000) < 120
    assert result["thd_percent"] > 5


def test_compare_clipping(tmp_path: Path) -> None:
    expected = tmp_path / "expected.csv"
    observed = tmp_path / "observed.csv"
    _write(expected, 1000)
    _write(observed, 1000, lambda _t, v: max(min(v, 0.45), -0.45))
    result = compare_waveform_spectra(expected, observed)
    assert result["mismatch_type"] == "clipping"
    assert result["confidence"] > 0.8
    assert result["observed_fft"]["top_harmonics"]


def test_compare_harmonic_distortion(tmp_path: Path) -> None:
    expected = tmp_path / "expected.csv"
    observed = tmp_path / "observed.csv"
    _write(expected, 1000)
    _write(observed, 1000, lambda t, v: v + 0.1 * math.sin(2 * math.pi * 3000 * t))
    result = compare_waveform_spectra(expected, observed)
    assert result["mismatch_type"] == "harmonic_distortion"


def test_compare_frequency_drift(tmp_path: Path) -> None:
    expected = tmp_path / "expected.csv"
    observed = tmp_path / "observed.csv"
    _write(expected, 1000)
    _write(observed, 950)
    result = compare_waveform_spectra(expected, observed)
    assert result["mismatch_type"] == "frequency_drift"
