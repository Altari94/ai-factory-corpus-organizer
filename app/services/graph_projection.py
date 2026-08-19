from collections.abc import Sequence
from uuid import UUID

from app.domain.discovery import CorpusGraph, GraphEdge, GraphNode
from app.domain.semantic import Episode, EpisodeEntity, EpisodeRelation, EpisodeTopic, Entity, Topic


class SemanticGraphProjector:
    """Pure projection; no PostgreSQL or graph database knowledge."""

    def project(
        self,
        episodes: Sequence[Episode],
        entities: Sequence[Entity],
        topics: Sequence[Topic],
        relations: Sequence[EpisodeRelation],
        episode_entities: Sequence[EpisodeEntity],
        episode_topics: Sequence[EpisodeTopic],
    ) -> CorpusGraph:
        nodes = [
            *(GraphNode(node_id=item.episode_id, node_type="EPISODE") for item in episodes),
            *(GraphNode(node_id=item.entity_id, node_type="ENTITY", label=item.canonical_name) for item in entities),
            *(GraphNode(node_id=item.topic_id, node_type="TOPIC", label=item.label) for item in topics),
        ]
        edges = [
            *(GraphEdge(from_node_id=item.from_episode_id, to_node_id=item.to_episode_id, edge_type=item.relation_type, confidence=item.confidence) for item in relations),
            *(GraphEdge(from_node_id=item.episode_id, to_node_id=item.entity_id, edge_type="MENTIONS") for item in episode_entities),
            *(GraphEdge(from_node_id=item.episode_id, to_node_id=item.topic_id, edge_type="IN_TOPIC") for item in episode_topics),
        ]
        return CorpusGraph(nodes=nodes, edges=edges)
