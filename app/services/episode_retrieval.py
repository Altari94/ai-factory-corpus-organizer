import math
from collections.abc import Sequence
from uuid import UUID

from app.domain.discovery import SimilarEpisodeCandidate


class InMemoryEpisodeRetriever:
    def __init__(self) -> None:
        self.vectors: dict[UUID, tuple[UUID, list[float], str, str]] = {}

    def add(self, episode_id: UUID, embedding_id: UUID, vector: list[float], profile_id: str, model_version: str) -> None:
        self.vectors[episode_id] = (embedding_id, vector, profile_id, model_version)

    def similar_episodes(self, episode_id: UUID, limit: int) -> list[SimilarEpisodeCandidate]:
        if limit <= 0 or episode_id not in self.vectors:
            return []
        source_embedding, source_vector, profile_id, model_version = self.vectors[episode_id]
        results = []
        for candidate_id, (embedding_id, vector, candidate_profile, candidate_version) in self.vectors.items():
            if candidate_id == episode_id or candidate_profile != profile_id or len(vector) != len(source_vector):
                continue
            results.append(SimilarEpisodeCandidate(
                source_episode_id=episode_id,
                candidate_episode_id=candidate_id,
                similarity_score=_cosine(source_vector, vector),
                embedding_id=embedding_id,
                embedding_profile_id=candidate_profile,
                model_version=candidate_version,
            ))
        return sorted(results, key=lambda item: item.similarity_score, reverse=True)[:limit]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
