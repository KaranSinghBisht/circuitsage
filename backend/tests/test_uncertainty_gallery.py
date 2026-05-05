from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from app.config import get_settings
from app.database import db, init_db, utc_now
from app.main import _insert_artifact, add_measurement
from app.schemas import MeasurementCreate
from app.services.agent_orchestrator import diagnose_session


ROOT = Path(__file__).resolve().parents[2]
GALLERY = ROOT / "sample_data" / "uncertainty"
CASES = sorted(path for path in GALLERY.iterdir() if path.is_dir())


async def fail_ollama(*args: Any, **kwargs: Any) -> dict[str, Any]:
    raise RuntimeError("ollama disabled in uncertainty-gallery test")


def _insert_session(session_id: str, expected: dict[str, Any]) -> None:
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO lab_sessions (id, title, student_level, experiment_type, status, created_at, updated_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                expected["title"],
                "2nd/3rd year EEE",
                expected.get("experiment_type", "unknown"),
                "bench",
                now,
                now,
                expected.get("missing", ""),
            ),
        )


def _attach_case_artifacts(session_id: str, case_dir: Path, expected: dict[str, Any]) -> None:
    netlist = case_dir / "netlist.net"
    note = case_dir / "note.txt"
    if netlist.exists():
        _insert_artifact(session_id, "netlist", netlist, "netlist.net")
    if note.exists():
        _insert_artifact(session_id, "note", note, "note.txt")
    if expected.get("breadboard_photo"):
        _insert_artifact(
            session_id,
            "breadboard",
            ROOT / "sample_data" / "op_amp_lab" / "breadboard_placeholder.png",
            "breadboard_placeholder.png",
        )


def _attach_measurements(session_id: str, expected: dict[str, Any]) -> None:
    for measurement in expected.get("measurements", []):
        add_measurement(
            session_id,
            MeasurementCreate(
                label=measurement["label"],
                value=float(measurement["value"]),
                unit=measurement.get("unit", "V"),
                mode=measurement.get("mode", "DC"),
                context=measurement.get("context", ""),
                source="uncertainty_gallery",
            ),
        )


def test_uncertainty_gallery_has_eight_cases() -> None:
    assert len(CASES) == 8
    for case_dir in CASES:
        assert (case_dir / "student_question.txt").exists()
        assert (case_dir / "expected_outcome.json").exists()
        assert (case_dir / "netlist.net").exists() or (case_dir / "note.txt").exists()


@pytest.mark.anyio
@pytest.mark.parametrize("case_dir", CASES, ids=[path.name for path in CASES])
async def test_uncertainty_gallery_case_returns_low_confidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_dir: Path,
) -> None:
    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fail_ollama)
    settings = get_settings()
    original_db_path = settings.database_path
    original_upload_dir = settings.upload_dir
    settings.database_path = tmp_path / f"{case_dir.name}.db"
    settings.upload_dir = tmp_path / "uploads"
    init_db()

    expected = json.loads((case_dir / "expected_outcome.json").read_text())
    session_id = str(uuid.uuid4())
    try:
        _insert_session(session_id, expected)
        _attach_case_artifacts(session_id, case_dir, expected)
        _attach_measurements(session_id, expected)

        result = await diagnose_session(session_id, (case_dir / "student_question.txt").read_text())
        diagnosis = result["diagnosis"]
        next_label = diagnosis.get("next_measurement", {}).get("label")

        if expected.get("safety_refusal"):
            assert next_label == "Stop live debugging"
        else:
            assert diagnosis["confidence"] == expected["expected_confidence"]
            assert next_label != "Stop live debugging"
        if expected.get("expected_next_label"):
            assert next_label == expected["expected_next_label"]
    finally:
        settings.database_path = original_db_path
        settings.upload_dir = original_upload_dir
