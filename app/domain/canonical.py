from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class CanonicalRun(BaseModel):
    model_config = ConfigDict(extra="ignore")

    run_id: UUID
    source_id: UUID
    schema_version: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None


class CanonicalDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_id: UUID
    source_id: UUID
    document_type: str
    title: str | None = None


class CanonicalUnit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    unit_id: UUID
    document_id: UUID
    processing_run_id: UUID
    unit_type: str
    sequence: int
    text: str
    parent_unit_id: UUID | None = None
    source_native_id: str | None = None
    original_timestamp: datetime | None = None
    speaker: str | None = None
    role: str | None = None
    source_locator: str | None = None
