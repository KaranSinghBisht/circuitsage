from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import get_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    db_path = get_settings().database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS lab_sessions (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              student_level TEXT NOT NULL,
              experiment_type TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS artifacts (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              kind TEXT NOT NULL,
              filename TEXT NOT NULL,
              path TEXT NOT NULL,
              text_excerpt TEXT NOT NULL DEFAULT '',
              metadata_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES lab_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS measurements (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              label TEXT NOT NULL,
              value REAL NOT NULL,
              unit TEXT NOT NULL,
              mode TEXT NOT NULL,
              context TEXT NOT NULL DEFAULT '',
              source TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES lab_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS diagnoses (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              diagnosis_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES lab_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              metadata_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES lab_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
              session_id TEXT PRIMARY KEY,
              markdown TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES lab_sessions(id) ON DELETE CASCADE
            );
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("metadata_json", "diagnosis_json"):
        if key in data and isinstance(data[key], str):
            data[key] = json.loads(data[key])
    return data


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(row) or {} for row in rows]


def read_text_excerpt(path: Path, limit: int = 1200) -> str:
    try:
        if path.suffix.lower() in {".md", ".txt", ".net", ".cir", ".csv", ".m", ".ino"}:
            return path.read_text(errors="ignore")[:limit]
    except OSError:
        return ""
    return ""

