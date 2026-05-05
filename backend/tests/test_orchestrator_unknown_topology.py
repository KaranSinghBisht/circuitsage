from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from app.database import db, init_db, utc_now
from app.services.agent_orchestrator import diagnose_session


@pytest.mark.anyio
async def test_orchestrator_unknown_topology_does_not_use_op_amp_answer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.config import get_settings

    settings = get_settings()
    original_db_path = settings.database_path
    settings.database_path = tmp_path / "unknown_topology.db"
    init_db()

    async def fail_ollama(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("ollama disabled in test")

    monkeypatch.setattr("app.services.agent_orchestrator.OllamaClient.chat", fail_ollama)

    session_id = str(uuid.uuid4())
    now = utc_now()
    try:
        with db() as conn:
            conn.execute(
                """
                INSERT INTO lab_sessions (id, title, student_level, experiment_type, status, created_at, updated_at, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    "Unknown lab symptom",
                    "2nd/3rd year EEE",
                    "unknown",
                    "bench",
                    now,
                    now,
                    "Output is wrong but no topology has been provided.",
                ),
            )

        result = await diagnose_session(session_id, "My circuit does not match simulation.")
        diagnosis = result["diagnosis"]

        assert diagnosis["experiment_type"] == "unknown"
        assert diagnosis["likely_faults"][0]["id"].startswith("unknown_")
        assert "non-inverting" not in json.dumps(diagnosis).lower()
    finally:
        settings.database_path = original_db_path
