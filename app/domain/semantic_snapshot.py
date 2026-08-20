"""Stable, consumer-facing projection of one F0.4 semantic run."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SemanticSnapshotObject(BaseModel):
    object_id: UUID
    object_type: str
    label: str | None = None
    description: str | None = None
    episode_ids: list[UUID] = Field(default_factory=list)
    evidence_unit_ids: list[UUID] = Field(default_factory=list)
    document_id: UUID | None = None
    sequence: int | None = Field(default=None, ge=0)
    occurred_at: datetime | None = None


class SemanticSnapshot(BaseModel):
    organizer_run_id: UUID
    schema_version: str = "1.0.0"
    topics: list[SemanticSnapshotObject] = Field(default_factory=list)
    threads: list[SemanticSnapshotObject] = Field(default_factory=list)
    entities: list[SemanticSnapshotObject] = Field(default_factory=list)
    episodes: list[SemanticSnapshotObject] = Field(default_factory=list)
    relations: list[SemanticSnapshotObject] = Field(default_factory=list)
