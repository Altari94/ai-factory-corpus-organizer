from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntityMention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: UUID
    canonical_name: str = Field(min_length=1)
    entity_type: str | None = None
    episode_id: UUID
    evidence_unit_ids: list[UUID] = Field(min_length=1)


class EntityExtractionResult(BaseModel):
    mentions: list[EntityMention]
    algorithm_version: str


class SimilarEpisodeCandidate(BaseModel):
    source_episode_id: UUID
    candidate_episode_id: UUID
    similarity_score: float = Field(ge=-1, le=1)
    embedding_id: UUID | None = None
    embedding_profile_id: str
    model_version: str


class RelationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_episode_id: UUID
    to_episode_id: UUID
    relation_type: Literal["SAME_THREAD", "RELATED", "UNRELATED", "UNCERTAIN"]
    confidence: float = Field(ge=0, le=1)
    evidence_unit_ids: list[UUID] = Field(min_length=1)


class GraphNode(BaseModel):
    node_id: UUID
    node_type: Literal["EPISODE", "ENTITY", "TOPIC"]
    label: str | None = None


class GraphEdge(BaseModel):
    from_node_id: UUID
    to_node_id: UUID
    edge_type: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class CorpusGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class TopicCluster(BaseModel):
    cluster_id: UUID
    episode_ids: list[UUID] = Field(min_length=1)
    algorithm_version: str
    parent_cluster_id: UUID | None = None
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoherenceDecision(BaseModel):
    cluster_id: UUID
    coherent: bool
    confidence: float = Field(ge=0, le=1)
    evidence_episode_ids: list[UUID] = Field(min_length=1)
    needs_more_evidence: bool = False


class ThreadComponent(BaseModel):
    episode_id: UUID
    sequence: int = Field(ge=0)


class LogicalThread(BaseModel):
    thread_id: UUID
    components: list[ThreadComponent] = Field(min_length=1)
    label: str | None = None
