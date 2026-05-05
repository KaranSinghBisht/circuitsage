from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


SessionStatus = Literal["pre_lab", "bench", "diagnosing", "resolved", "archived"]
ArtifactKind = Literal["manual", "netlist", "waveform_csv", "image", "matlab", "tinkercad_code", "note"]


class LabSessionCreate(BaseModel):
    title: str
    student_level: str = "2nd/3rd year EEE"
    notes: str = ""
    experiment_type: str = "op_amp_inverting"


class LabSessionUpdate(BaseModel):
    title: str | None = None
    student_level: str | None = None
    status: SessionStatus | None = None
    summary: str | None = None


class LabSession(BaseModel):
    id: str
    title: str
    student_level: str
    experiment_type: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    summary: str


class Artifact(BaseModel):
    id: str
    session_id: str
    kind: ArtifactKind
    filename: str
    path: str
    text_excerpt: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MeasurementCreate(BaseModel):
    label: str
    value: float
    unit: str = "V"
    mode: str = "DC"
    context: str = ""
    source: str = "manual_entry"


class Measurement(BaseModel):
    id: str
    session_id: str
    label: str
    value: float
    unit: str
    mode: str
    context: str
    source: str
    created_at: datetime


class ChatRequest(BaseModel):
    message: str
    mode: Literal["pre_lab", "bench", "report"] = "bench"


class DiagnosisRequest(BaseModel):
    message: str | None = None


class Diagnosis(BaseModel):
    id: str
    session_id: str
    diagnosis_json: dict[str, Any]
    created_at: datetime


class Report(BaseModel):
    session_id: str
    markdown: str


class CompanionAnalyzeRequest(BaseModel):
    question: str = ""
    image_data_url: str | None = None
    app_hint: str = "auto"
    session_id: str | None = None
    save_snapshot: bool = False
