from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmbeddingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    provider: str
    model_name: str
    model_version: str
    dimensions: int = Field(gt=0)
    distance_metric: str = "cosine"
    parameters: dict[str, Any] = Field(default_factory=dict)


class EmbeddingInput(BaseModel):
    canonical_unit_id: UUID
    text: str


class EmbeddingOutput(BaseModel):
    canonical_unit_id: UUID
    profile_id: str
    model_version: str
    vector: list[float]

    @model_validator(mode="after")
    def vector_not_empty(self) -> "EmbeddingOutput":
        if not self.vector:
            raise ValueError("embedding vector must not be empty")
        return self


class StoredEmbedding(BaseModel):
    embedding_id: UUID
    organizer_run_id: UUID
    canonical_unit_id: UUID
    profile_id: str
    model_version: str
    dimensions: int = Field(gt=0)
    vector: list[float]
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimilarityQuery(BaseModel):
    profile_id: str
    vector: list[float]
    limit: int = Field(gt=0)
    threshold: float | None = Field(default=None, ge=-1, le=1)


class SimilarityResult(BaseModel):
    embedding_id: UUID
    canonical_unit_id: UUID
    profile_id: str
    model_version: str
    similarity: float

