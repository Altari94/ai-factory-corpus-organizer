from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.llm import BoundaryDecision, ContextChunk, ContextUnit, LLMExecutionTrace
from app.domain.semantic import Episode


class BoundaryCandidateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threshold: float = Field(ge=0, le=1)
    speaker_change_weight: float = Field(ge=0, le=1)
    lexical_shift_weight: float = Field(ge=0, le=1)
    sequence_gap_weight: float = Field(ge=0, le=1)


class BoundaryCandidate(BaseModel):
    candidate_id: UUID
    left_unit_id: UUID
    right_unit_id: UUID
    score: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    signals: dict[str, float]
    evidence_unit_ids: list[UUID]
    requires_llm: bool = True


class BoundaryContext(BaseModel):
    candidate_id: UUID
    chunks: list[ContextChunk]
    canonical_unit_ids: list[UUID]


class BoundaryJudgeResult(BaseModel):
    decision: BoundaryDecision
    trace: LLMExecutionTrace


class EpisodeMembership(BaseModel):
    organizer_run_id: UUID
    episode_id: UUID
    canonical_unit_id: UUID
    sequence: int = Field(ge=0)


class EpisodeBuildResult(BaseModel):
    episodes: list[Episode]
    memberships: list[EpisodeMembership]

