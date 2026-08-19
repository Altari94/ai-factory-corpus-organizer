from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID, uuid5

from app.domain.discovery import TopicCluster
from app.domain.discovery import SimilarEpisodeCandidate


class SimilarityClusterer:
    """Threshold graph clustering; singleton and unassigned outcomes remain valid."""

    def cluster(
        self,
        episode_ids: Sequence[UUID],
        similarities: Sequence[SimilarEpisodeCandidate],
        *,
        threshold: float,
        algorithm_version: str = "similarity-components-v1",
    ) -> list[TopicCluster]:
        parent: dict[UUID, UUID] = {episode_id: episode_id for episode_id in episode_ids}

        def find(item: UUID) -> UUID:
            while parent[item] != item:
                parent[item] = parent[parent[item]]
                item = parent[item]
            return item

        def union(left: UUID, right: UUID) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for similarity in similarities:
            if similarity.similarity_score >= threshold and similarity.source_episode_id in parent and similarity.candidate_episode_id in parent:
                union(similarity.source_episode_id, similarity.candidate_episode_id)
        groups: dict[UUID, list[UUID]] = defaultdict(list)
        for episode_id in episode_ids:
            groups[find(episode_id)].append(episode_id)
        return [
            TopicCluster(
                cluster_id=uuid5(UUID(int=0), f"{algorithm_version}:{','.join(sorted(str(item) for item in members))}"),
                episode_ids=members,
                algorithm_version=algorithm_version,
            )
            for members in groups.values()
        ]
