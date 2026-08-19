from collections import defaultdict
from uuid import UUID

from app.domain.catalogue import CatalogueTopic, CorpusCatalogue, CorpusStatistics
from app.ports.semantic import SemanticReadPort


class CatalogueNotFoundError(LookupError):
    pass


class CatalogueBuilder:
    """Build a fresh personal overview from one immutable organizer run."""

    def __init__(self, semantic_reader: SemanticReadPort) -> None:
        self.semantic_reader = semantic_reader

    def build(self, organizer_run_id: UUID) -> CorpusCatalogue:
        if self.semantic_reader.get_run(organizer_run_id) is None:
            raise CatalogueNotFoundError(f"Organizer run not found: {organizer_run_id}")
        episodes = self.semantic_reader.get_episodes(organizer_run_id)
        entities = self.semantic_reader.get_entities(organizer_run_id)
        topics = self.semantic_reader.get_topics(organizer_run_id)
        relations = self.semantic_reader.get_episode_relations(organizer_run_id)
        threads = self.semantic_reader.get_threads(organizer_run_id)
        episode_entities = self.semantic_reader.get_episode_entities(organizer_run_id)
        episode_topics = self.semantic_reader.get_episode_topics(organizer_run_id)
        thread_episodes = self.semantic_reader.get_thread_episodes(organizer_run_id)

        episode_to_topic = defaultdict(set)
        for link in episode_topics:
            episode_to_topic[link.episode_id].add(link.topic_id)
        entities_by_episode = defaultdict(set)
        for link in episode_entities:
            entities_by_episode[link.episode_id].add(link.entity_id)
        threads_by_episode = defaultdict(set)
        for link in thread_episodes:
            threads_by_episode[link.episode_id].add(link.thread_id)
        episodes_by_topic = defaultdict(list)
        for link in episode_topics:
            episodes_by_topic[link.topic_id].append(link.episode_id)
        episode_index = {episode.episode_id: episode for episode in episodes}

        catalogue_topics = []
        for topic in sorted(topics, key=lambda item: (item.label.casefold(), str(item.topic_id))):
            topic_episode_ids = list(dict.fromkeys(episodes_by_topic[topic.topic_id]))
            topic_episode_set = set(topic_episode_ids)
            catalogue_topics.append(
                CatalogueTopic(
                    topic_id=topic.topic_id,
                    label=topic.label,
                    description=topic.description,
                    parent_topic_id=topic.parent_topic_id,
                    episode_count=len(topic_episode_ids),
                    document_ids=sorted(
                        {episode_index[episode_id].document_id for episode_id in topic_episode_set if episode_id in episode_index},
                        key=str,
                    ),
                    entity_ids=sorted(
                        {entity_id for episode_id in topic_episode_set for entity_id in entities_by_episode[episode_id]},
                        key=str,
                    ),
                    thread_ids=sorted(
                        {thread_id for episode_id in topic_episode_set for thread_id in threads_by_episode[episode_id]},
                        key=str,
                    ),
                    relation_count=sum(
                        relation.from_episode_id in topic_episode_set or relation.to_episode_id in topic_episode_set
                        for relation in relations
                    ),
                )
            )

        assigned = set(episode_to_topic)
        statistics = CorpusStatistics(
            organizer_run_id=organizer_run_id,
            episode_count=len(episodes),
            topic_count=len(topics),
            entity_count=len(entities),
            thread_count=len(threads),
            relation_count=len(relations),
            document_count=len({episode.document_id for episode in episodes}),
            assigned_episode_count=len(assigned),
            unassigned_episode_count=len({episode.episode_id for episode in episodes} - assigned),
            singleton_topic_count=sum(item.episode_count == 1 for item in catalogue_topics),
        )
        return CorpusCatalogue(
            organizer_run_id=organizer_run_id,
            topics=catalogue_topics,
            statistics=statistics,
        )
