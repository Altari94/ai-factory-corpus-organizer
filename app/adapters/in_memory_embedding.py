import hashlib
import math
from collections.abc import Sequence
from uuid import UUID

from app.domain.embedding import (
    EmbeddingInput,
    EmbeddingOutput,
    SimilarityQuery,
    SimilarityResult,
    StoredEmbedding,
)


class InMemoryEmbeddingAdapter:
    """Deterministic test adapter; embeddings remain search signals only."""

    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    def embed(self, profile_id: str, inputs: Sequence[EmbeddingInput]) -> list[EmbeddingOutput]:
        return [
            EmbeddingOutput(
                canonical_unit_id=item.canonical_unit_id,
                profile_id=profile_id,
                model_version="in-memory-v1",
                vector=self._vector(item.text),
            )
            for item in inputs
        ]

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [((digest[index] / 255.0) * 2) - 1 for index in range(self.dimensions)]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.embeddings: dict[UUID, StoredEmbedding] = {}

    def save(self, embeddings: Sequence[StoredEmbedding]) -> None:
        for embedding in embeddings:
            self.embeddings[embedding.embedding_id] = embedding

    def similarity_search(self, query: SimilarityQuery) -> list[SimilarityResult]:
        results = []
        for embedding in self.embeddings.values():
            if embedding.profile_id != query.profile_id or len(embedding.vector) != len(query.vector):
                continue
            similarity = _cosine(query.vector, embedding.vector)
            if query.threshold is None or similarity >= query.threshold:
                results.append(
                    SimilarityResult(
                        embedding_id=embedding.embedding_id,
                        canonical_unit_id=embedding.canonical_unit_id,
                        profile_id=embedding.profile_id,
                        model_version=embedding.model_version,
                        similarity=similarity,
                    )
                )
        return sorted(results, key=lambda result: result.similarity, reverse=True)[: query.limit]


def _cosine(left: list[float], right: list[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)

