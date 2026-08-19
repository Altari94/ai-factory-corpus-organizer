from uuid import UUID

from pydantic import BaseModel, Field


class CatalogueTopic(BaseModel):
    """A human-readable, run-scoped view of one derived topic."""

    topic_id: UUID
    label: str
    description: str | None = None
    parent_topic_id: UUID | None = None
    episode_count: int = Field(ge=0)
    document_ids: list[UUID]
    entity_ids: list[UUID]
    thread_ids: list[UUID]
    relation_count: int = Field(ge=0)


class CorpusStatistics(BaseModel):
    organizer_run_id: UUID
    episode_count: int = Field(ge=0)
    topic_count: int = Field(ge=0)
    entity_count: int = Field(ge=0)
    thread_count: int = Field(ge=0)
    relation_count: int = Field(ge=0)
    document_count: int = Field(ge=0)
    assigned_episode_count: int = Field(ge=0)
    unassigned_episode_count: int = Field(ge=0)
    singleton_topic_count: int = Field(ge=0)


class CorpusCatalogue(BaseModel):
    organizer_run_id: UUID
    topics: list[CatalogueTopic]
    statistics: CorpusStatistics
