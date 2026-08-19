from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from app.domain.discovery import EntityExtractionResult, RelationDecision, SimilarEpisodeCandidate
from app.domain.llm import ContextUnit
from app.domain.semantic import Episode


@runtime_checkable
class EntityExtractionPort(Protocol):
    def extract(self, episode: Episode, units: Sequence[ContextUnit]) -> EntityExtractionResult: ...


@runtime_checkable
class EpisodeRetrievalPort(Protocol):
    def similar_episodes(self, episode_id: UUID, limit: int) -> list[SimilarEpisodeCandidate]: ...


@runtime_checkable
class RelationJudgePort(Protocol):
    def judge(self, source: Episode, candidate: Episode, units: Sequence[ContextUnit]) -> RelationDecision: ...
