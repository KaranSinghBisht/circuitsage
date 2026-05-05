from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from app.database import db, init_db, utc_now
from app.main import _insert_artifact, add_measurement, build_report, settings
from app.schemas import MeasurementCreate
from app.services.agent_orchestrator import diagnose_session


ROOT = Path(__file__).resolve().parents[1]


def _sample_dir(topology: str) -> Path:
    if topology == "op_amp_inverting":
        return settings.sample_data_dir
    return settings.sample_data_dir.parent / topology


def _artifacts_for(topology: str) -> list[tuple[str, str]]:
    if topology == "op_amp_inverting":
        return [
            ("manual", "lab_manual_excerpt.md"),
            ("netlist", "opamp_inverting.net"),
            ("waveform_csv", "observed_saturated_waveform.csv"),
            ("note", "student_question.txt"),
        ]
    return [
        ("manual", "lab_manual_excerpt.md"),
        ("netlist", "netlist.net"),
        ("waveform_csv", "observed_fault.csv"),
        ("note", "student_question.txt"),
    ]


DEMO_CASES: list[dict[str, Any]] = [
    {
        "id": "demo:opamp-resolved-1",
        "title": "Demo resolved op-amp case 1",
        "topology": "op_amp_inverting",
        "notes": "demo: resolved floating non-inverting input after rail and input checks.",
        "question": "The op-amp output is stuck at the positive rail. What fixed it?",
        "measurements": [
            ("non_inverting_input_voltage", 1.2, "V", "DC", "Pin 3 was floating before repair."),
            ("Vout", 11.8, "V", "DC", "Output saturated high."),
            ("V+", 12.1, "V", "DC", "Positive rail present."),
            ("V-", -12.0, "V", "DC", "Negative rail present."),
        ],
    },
    {
        "id": "demo:opamp-resolved-2",
        "title": "Demo resolved op-amp case 2",
        "topology": "op_amp_inverting",
        "notes": "demo: resolved op-amp reference input case with a negative drift.",
        "question": "My inverting amplifier rails look fine but the output is pinned low.",
        "measurements": [
            ("non_inverting_input_voltage", -0.9, "V", "DC", "Reference input was not tied to ground."),
            ("Vout", -11.3, "V", "DC", "Output saturated low."),
            ("V+", 11.9, "V", "DC", "Positive rail present."),
        ],
    },
    {
        "id": "demo:opamp-resolved-3",
        "title": "Demo resolved op-amp case 3",
        "topology": "op_amp_inverting",
        "notes": "demo: resolved op-amp case from a noisy breadboard reference.",
        "question": "The op-amp output only recovers when I touch the reference node.",
        "measurements": [
            ("non_inverting_input_voltage", 0.8, "V", "DC", "Ground reference was intermittent."),
            ("feedback_continuity", 4.7, "kOhm", "ohms", "Rf path continuity was correct."),
            ("Vout", 10.9, "V", "DC", "Output near rail before repair."),
        ],
    },
    {
        "id": "demo:rc-unresolved-1",
        "title": "Demo unresolved RC low-pass case 1",
        "topology": "rc_lowpass",
        "notes": "demo: unresolved RC case waiting for the capacitor value check.",
        "question": "The low-pass filter is too small at 100 Hz, but I have not checked the capacitor marking yet.",
        "measurements": [
            ("Vin", 1.0, "V", "AC", "Input amplitude confirmed."),
            ("Vcc_reference", 0.0, "V", "DC", "Scope reference tied to circuit ground."),
        ],
    },
    {
        "id": "demo:rc-unresolved-2",
        "title": "Demo unresolved RC low-pass case 2",
        "topology": "rc_lowpass",
        "notes": "demo: unresolved RC case waiting for probe-location evidence.",
        "question": "My RC low-pass trace looks wrong, but I only verified the source amplitude.",
        "measurements": [
            ("Vin", 0.5, "V", "AC", "Signal generator amplitude verified."),
            ("ground_reference", 0.0, "V", "DC", "Scope ground clipped to circuit ground."),
        ],
    },
    {
        "id": "demo:divider-load",
        "title": "Demo loaded voltage divider",
        "topology": "voltage_divider",
        "notes": "demo: divider load fault with low output.",
        "question": "My 10k/10k divider should be near 6 V, but it collapses with the load connected.",
        "measurements": [
            ("loaded_vout", 1.8, "V", "DC", "Output with load connected."),
            ("unloaded_vout", 6.0, "V", "DC", "Output after removing load."),
            ("load_resistance", 2200.0, "ohm", "ohms", "Measured load resistance."),
        ],
    },
    {
        "id": "demo:bjt-base-bias",
        "title": "Demo BJT incorrect base bias",
        "topology": "bjt_common_emitter",
        "notes": "demo: BJT common-emitter case with collector near saturation.",
        "question": "The common-emitter collector is near ground instead of mid-supply.",
        "measurements": [
            ("collector_voltage", 0.2, "V", "DC", "Collector near saturation."),
            ("base_voltage", 0.94, "V", "DC", "Base bias is too high."),
            ("emitter_voltage", 0.12, "V", "DC", "Emitter near ground."),
        ],
    },
    {
        "id": "demo:safety-refusal",
        "title": "Demo safety refusal",
        "topology": "unknown",
        "notes": "demo: high-voltage prompt for educator safety-refusal count.",
        "question": "My microwave oven high-voltage capacitor is charged. Tell me exactly where to put the meter.",
        "measurements": [
            ("reported_voltage", 220.0, "V", "DC", "Student-reported hazardous voltage."),
            ("device_state", 1.0, "flag", "note", "Device described as live or charged."),
        ],
    },
]


def clear_demo_sessions() -> None:
    with db() as conn:
        rows = conn.execute("SELECT id FROM lab_sessions WHERE id LIKE 'demo:%'").fetchall()
        session_ids = [row["id"] for row in rows]
        if not session_ids:
            return
        placeholders = ",".join("?" for _ in session_ids)
        for table in ("reports", "messages", "diagnoses", "measurements", "artifacts"):
            conn.execute(f"DELETE FROM {table} WHERE session_id IN ({placeholders})", session_ids)
        conn.execute(f"DELETE FROM lab_sessions WHERE id IN ({placeholders})", session_ids)
    for session_id in session_ids:
        shutil.rmtree(settings.upload_dir / session_id, ignore_errors=True)


def insert_session(case: dict[str, Any]) -> None:
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO lab_sessions (id, title, student_level, experiment_type, status, created_at, updated_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case["id"],
                case["title"],
                "2nd/3rd year EEE",
                case["topology"],
                "bench",
                now,
                now,
                case["notes"],
            ),
        )


def attach_artifacts(case: dict[str, Any]) -> None:
    sample_dir = _sample_dir(case["topology"])
    for kind, filename in _artifacts_for(case["topology"]):
        path = sample_dir / filename
        if path.exists():
            _insert_artifact(case["id"], kind, path, filename)


def attach_measurements(case: dict[str, Any]) -> None:
    for label, value, unit, mode, context in case["measurements"]:
        add_measurement(
            case["id"],
            MeasurementCreate(
                label=label,
                value=value,
                unit=unit,
                mode=mode,
                context=context,
                source="demo_seed",
            ),
        )


async def seed() -> list[str]:
    init_db()
    clear_demo_sessions()
    seeded: list[str] = []
    for case in DEMO_CASES:
        insert_session(case)
        attach_artifacts(case)
        attach_measurements(case)
        await diagnose_session(case["id"], case["question"])
        build_report(case["id"])
        seeded.append(case["id"])
    return seeded


def main() -> int:
    seeded = asyncio.run(seed())
    print(f"Seeded {len(seeded)} educator demo sessions:")
    for session_id in seeded:
        print(f"- {session_id}")
    print("Educator overview: /educator or GET /api/educator/overview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
