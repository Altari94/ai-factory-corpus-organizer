from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.domain.embedding import (
    EmbeddingInput,
    EmbeddingOutput,
    SimilarityQuery,
    SimilarityResult,
    StoredEmbedding,
)


@runtime_checkable
class EmbeddingPort(Protocol):
    def embed(self, profile_id: str, inputs: Sequence[EmbeddingInput]) -> list[EmbeddingOutput]: ...


@runtime_checkable
class VectorStorePort(Protocol):
    def save(self, embeddings: Sequence[StoredEmbedding]) -> None: ...

    def similarity_search(self, query: SimilarityQuery) -> list[SimilarityResult]: ...

