"""Provider-neutral read models exposed by F0.4 to later consumers."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


CORPUS_READ_CONTRACT_VERSION = "1.0.0"


class SourceReference(BaseModel):
    source_id: UUID
    document_id: UUID
    source_title: str | None = None
    source_locator: str | None = None


class ContentUnitView(BaseModel):
    content_unit_id: UUID
    source_id: UUID
    document_id: UUID
    episode_id: UUID
    sequence: int = Field(ge=0)
    original_timestamp: datetime | None = None
    source_title: str | None = None
    speaker: str | None = None
    role: str | None = None
    original_text: str
    source_locator: str | None = None
    topic_ids: list[UUID] = Field(default_factory=list)
    thread_ids: list[UUID] = Field(default_factory=list)


class EpisodeView(BaseModel):
    episode_id: UUID
    document_id: UUID
    sequence: int = Field(ge=0)
    timestamp: datetime | None = None
    topic_ids: list[UUID] = Field(default_factory=list)
    thread_ids: list[UUID] = Field(default_factory=list)
    content_units: list[ContentUnitView] = Field(default_factory=list)
    provenance: list[SourceReference] = Field(default_factory=list)


class SourceView(BaseModel):
    source_id: UUID
    source_title: str | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    episode_ids: list[UUID] = Field(default_factory=list)


class TopicNode(BaseModel):
    topic_id: UUID
    label: str
    description: str | None = None
    parent_topic_id: UUID | None = None
    child_topic_ids: list[UUID] = Field(default_factory=list)
    episode_count: int = Field(ge=0)


class TopicDetail(TopicNode):
    episode_ids: list[UUID] = Field(default_factory=list)
    entity_ids: list[UUID] = Field(default_factory=list)
    thread_ids: list[UUID] = Field(default_factory=list)


class ThreadView(BaseModel):
    thread_id: UUID
    label: str
    description: str | None = None
    episode_ids: list[UUID] = Field(default_factory=list)


class EntityView(BaseModel):
    entity_id: UUID
    canonical_name: str
    entity_type: str | None = None
    episode_ids: list[UUID] = Field(default_factory=list)
    evidence_unit_ids: list[UUID] = Field(default_factory=list)


class CorpusCatalogue(BaseModel):
    organizer_run_id: UUID
    contract_version: str = CORPUS_READ_CONTRACT_VERSION
    topics: list[TopicNode] = Field(default_factory=list)


class CorpusSlice(BaseModel):
    organizer_run_id: UUID
    contract_version: str = CORPUS_READ_CONTRACT_VERSION
    selected_topic_ids: list[UUID] = Field(default_factory=list)
    included_topic_ids: list[UUID] = Field(default_factory=list)
    episodes: list[EpisodeView] = Field(default_factory=list)
    provenance: list[SourceReference] = Field(default_factory=list)
