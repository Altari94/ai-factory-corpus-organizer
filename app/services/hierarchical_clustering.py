from collections.abc import Sequence
from uuid import UUID, uuid5

from app.domain.discovery import SimilarEpisodeCandidate, TopicCluster
from app.services.topic_clustering import SimilarityClusterer


class RecursiveClusterer:
    def __init__(self, base: SimilarityClusterer | None = None) -> None:
        self.base = base or SimilarityClusterer()

    def cluster(
        self,
        episode_ids: Sequence[UUID],
        similarities: Sequence[SimilarEpisodeCandidate],
        *,
        threshold: float,
        algorithm_version: str = "recursive-similarity-v1",
        max_depth: int | None = None,
        depth: int = 0,
    ) -> list[TopicCluster]:
        clusters = self.base.cluster(episode_ids, similarities, threshold=threshold, algorithm_version=algorithm_version)
        if max_depth is not None and depth >= max_depth:
            return [cluster.model_copy(update={"metadata": {"depth": depth}}) for cluster in clusters]
        return [
            cluster.model_copy(update={"metadata": {"depth": depth}})
            for cluster in clusters
        ]
