from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrganizerRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class OrganizerRun(BaseModel):
    """Versioned execution context for all derived organizer data."""

    model_config = ConfigDict(extra="ignore")

    organizer_run_id: UUID
    corpus_id: UUID
    code_version: str
    algorithm_version: str
    semantic_schema_version: str
    started_at: datetime
    finished_at: datetime | None = None
    status: OrganizerRunStatus = OrganizerRunStatus.RUNNING
    configuration: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class DerivedObject(BaseModel):
    """Common provenance boundary for every semantic result."""

    model_config = ConfigDict(extra="ignore")

    organizer_run_id: UUID


class EpisodeStatus(StrEnum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class Episode(DerivedObject):
    """A derived chronological span over canonical units."""

    episode_id: UUID
    document_id: UUID
    start_unit_id: UUID
    end_unit_id: UUID
    sequence: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: EpisodeStatus = EpisodeStatus.PROPOSED


class Entity(DerivedObject):
    entity_id: UUID
    canonical_name: str
    entity_type: str | None = None


class Topic(DerivedObject):
    topic_id: UUID
    label: str
    parent_topic_id: UUID | None = None


class EpisodeRelation(DerivedObject):
    relation_id: UUID
    from_episode_id: UUID
    to_episode_id: UUID
    relation_type: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class Thread(DerivedObject):
    thread_id: UUID
    label: str
    description: str | None = None


class EpisodeEntity(DerivedObject):
    link_id: UUID
    episode_id: UUID
    entity_id: UUID


class EpisodeTopic(DerivedObject):
    link_id: UUID
    episode_id: UUID
    topic_id: UUID


class TopicRelation(DerivedObject):
    relation_id: UUID
    parent_topic_id: UUID
    child_topic_id: UUID
    relation_type: str = "PARENT_OF"


class ThreadEpisode(DerivedObject):
    link_id: UUID
    thread_id: UUID
    episode_id: UUID
    sequence: int = Field(ge=0)
