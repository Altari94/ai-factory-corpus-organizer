from collections.abc import Sequence

from app.domain.discovery import CoherenceDecision, TopicCluster


class RepresentativeContextSelector:
    def select(self, cluster: TopicCluster, texts_by_episode: dict, max_items: int = 5) -> list[str]:
        return [texts_by_episode[episode_id] for episode_id in cluster.episode_ids if episode_id in texts_by_episode][:max_items]


class HeuristicCoherenceJudge:
    def judge(self, cluster: TopicCluster, representative_texts: Sequence[str]) -> CoherenceDecision:
        tokens = [set(text.casefold().split()) for text in representative_texts]
        overlap = len(set.intersection(*tokens)) if tokens else 0
        coherent = bool(tokens) and (len(tokens) == 1 or overlap > 0)
        return CoherenceDecision(
            cluster_id=cluster.cluster_id,
            coherent=coherent,
            confidence=0.6 if coherent else 0.4,
            evidence_episode_ids=cluster.episode_ids[: max(1, min(3, len(cluster.episode_ids)))],
            needs_more_evidence=len(cluster.episode_ids) > len(representative_texts),
        )
