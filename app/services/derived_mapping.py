from collections.abc import Sequence
from uuid import UUID, uuid5

from app.domain.discovery import EntityExtractionResult, LogicalThread, TopicCluster
from app.domain.semantic import Entity, EpisodeEntity, EpisodeRelation, EpisodeTopic, Thread, ThreadEpisode, Topic


def entities_for_run(run_id: UUID, result: EntityExtractionResult) -> tuple[list[Entity], list[EpisodeEntity]]:
    entities: dict[UUID, Entity] = {}
    links: list[EpisodeEntity] = []
    for mention in result.mentions:
        entities.setdefault(mention.entity_id, Entity(organizer_run_id=run_id, entity_id=mention.entity_id, canonical_name=mention.canonical_name, entity_type=mention.entity_type))
        links.append(EpisodeEntity(organizer_run_id=run_id, link_id=uuid5(run_id, f"episode-entity:{mention.episode_id}:{mention.entity_id}"), episode_id=mention.episode_id, entity_id=mention.entity_id, evidence_unit_ids=mention.evidence_unit_ids))
    return list(entities.values()), links


def topics_for_run(run_id: UUID, clusters: Sequence[TopicCluster]) -> tuple[list[Topic], list[EpisodeTopic]]:
    topics = [Topic(organizer_run_id=run_id, topic_id=cluster.cluster_id, label=cluster.label or "Unassigned", description=cluster.metadata.get("description"), parent_topic_id=cluster.parent_cluster_id) for cluster in clusters]
    links = [EpisodeTopic(organizer_run_id=run_id, link_id=uuid5(run_id, f"episode-topic:{cluster.cluster_id}:{episode_id}"), episode_id=episode_id, topic_id=cluster.cluster_id) for cluster in clusters for episode_id in cluster.episode_ids]
    return topics, links


def threads_for_run(run_id: UUID, threads: Sequence[LogicalThread]) -> tuple[list[Thread], list[ThreadEpisode]]:
    result_threads = [Thread(organizer_run_id=run_id, thread_id=thread.thread_id, label=thread.label or "Unlabelled thread") for thread in threads]
    links = [ThreadEpisode(organizer_run_id=run_id, link_id=uuid5(run_id, f"thread-episode:{thread.thread_id}:{component.episode_id}"), thread_id=thread.thread_id, episode_id=component.episode_id, sequence=component.sequence) for thread in threads for component in thread.components]
    return result_threads, links


def relation_for_run(run_id: UUID, decision) -> EpisodeRelation:
    return EpisodeRelation(organizer_run_id=run_id, relation_id=uuid5(run_id, f"relation:{decision.from_episode_id}:{decision.to_episode_id}"), from_episode_id=decision.from_episode_id, to_episode_id=decision.to_episode_id, relation_type=decision.relation_type, confidence=decision.confidence, evidence_unit_ids=decision.evidence_unit_ids)
