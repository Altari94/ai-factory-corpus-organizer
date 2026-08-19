"""Run-scoped persistence workflow for discovery outputs."""

from collections.abc import Sequence

from app.domain.episode_detection import EpisodeMembership
from app.domain.semantic import (
    Entity,
    Episode,
    EpisodeEntity,
    EpisodeRelation,
    EpisodeTopic,
    OrganizerRun,
    Thread,
    ThreadEpisode,
    Topic,
    TopicRelation,
)
from app.ports.semantic import SemanticWritePort


class DiscoveryPersistenceService:
    """Persist derived data without depending on Supabase or SQL types."""

    def __init__(self, writer: SemanticWritePort) -> None:
        self.writer = writer

    def persist(
        self,
        run: OrganizerRun,
        *,
        episodes: Sequence[Episode],
        memberships: Sequence[EpisodeMembership] = (),
        entities: Sequence[Entity] = (),
        episode_entities: Sequence[EpisodeEntity] = (),
        topics: Sequence[Topic] = (),
        episode_topics: Sequence[EpisodeTopic] = (),
        topic_relations: Sequence[TopicRelation] = (),
        relations: Sequence[EpisodeRelation] = (),
        threads: Sequence[Thread] = (),
        thread_episodes: Sequence[ThreadEpisode] = (),
        create_run: bool = True,
    ) -> None:
        if create_run:
            self.writer.create_run(run)
        self.writer.write_episodes(episodes)
        self.writer.write_episode_memberships(memberships)
        self.writer.write_entities(entities)
        self.writer.write_episode_entities(episode_entities)
        self.writer.write_topics(topics)
        self.writer.write_episode_topics(episode_topics)
        self.writer.write_topic_relations(topic_relations)
        self.writer.write_episode_relations(relations)
        self.writer.write_threads(threads)
        self.writer.write_thread_episodes(thread_episodes)
