from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.domain.semantic import (
    Entity,
    Episode,
    EpisodeEntity,
    EpisodeRelation,
    EpisodeTopic,
    OrganizerRun,
    OrganizerRunStatus,
    Thread,
    ThreadEpisode,
    Topic,
    TopicRelation,
)
from app.domain.episode_detection import EpisodeMembership


class InMemorySemanticAdapter:
    """Reference adapter used by local development and contract tests."""

    def __init__(self) -> None:
        self.runs: dict[UUID, OrganizerRun] = {}
        self.episodes: dict[UUID, Episode] = {}
        self.episode_memberships: dict[tuple[UUID, UUID], EpisodeMembership] = {}
        self.entities: dict[UUID, Entity] = {}
        self.topics: dict[UUID, Topic] = {}
        self.episode_relations: dict[UUID, EpisodeRelation] = {}
        self.threads: dict[UUID, Thread] = {}
        self.episode_entities: dict[UUID, EpisodeEntity] = {}
        self.episode_topics: dict[UUID, EpisodeTopic] = {}
        self.topic_relations: dict[UUID, TopicRelation] = {}
        self.thread_episodes: dict[UUID, ThreadEpisode] = {}

    def create_run(self, run: OrganizerRun) -> None:
        if run.organizer_run_id in self.runs:
            raise ValueError(f"Organizer run already exists: {run.organizer_run_id}")
        self.runs[run.organizer_run_id] = run

    def write_episodes(self, episodes: Sequence[Episode]) -> None:
        self._write(self.episodes, episodes, "episode_id")

    def write_episode_memberships(self, memberships: Sequence[EpisodeMembership]) -> None:
        for membership in memberships:
            self.episode_memberships[(membership.episode_id, membership.canonical_unit_id)] = membership

    def write_entities(self, entities: Sequence[Entity]) -> None:
        self._write(self.entities, entities, "entity_id")

    def write_topics(self, topics: Sequence[Topic]) -> None:
        self._write(self.topics, topics, "topic_id")

    def write_episode_relations(self, relations: Sequence[EpisodeRelation]) -> None:
        self._write(self.episode_relations, relations, "relation_id")

    def write_threads(self, threads: Sequence[Thread]) -> None:
        self._write(self.threads, threads, "thread_id")

    def write_episode_entities(self, links: Sequence[EpisodeEntity]) -> None:
        self._write(self.episode_entities, links, "link_id")

    def write_episode_topics(self, links: Sequence[EpisodeTopic]) -> None:
        self._write(self.episode_topics, links, "link_id")

    def write_topic_relations(self, relations: Sequence[TopicRelation]) -> None:
        self._write(self.topic_relations, relations, "relation_id")

    def write_thread_episodes(self, links: Sequence[ThreadEpisode]) -> None:
        self._write(self.thread_episodes, links, "link_id")

    def complete_run(self, run_id: UUID, finished_at: datetime) -> None:
        self._update_run(run_id, finished_at, OrganizerRunStatus.SUCCEEDED, None)

    def fail_run(self, run_id: UUID, finished_at: datetime, error: str) -> None:
        self._update_run(run_id, finished_at, OrganizerRunStatus.FAILED, error)

    def get_run(self, run_id: UUID) -> OrganizerRun | None:
        return self.runs.get(run_id)

    def get_episodes(self, run_id: UUID) -> list[Episode]:
        return self._for_run(self.episodes, run_id)

    def get_entities(self, run_id: UUID) -> list[Entity]:
        return self._for_run(self.entities, run_id)

    def get_topics(self, run_id: UUID) -> list[Topic]:
        return self._for_run(self.topics, run_id)

    def get_episode_relations(self, run_id: UUID) -> list[EpisodeRelation]:
        return self._for_run(self.episode_relations, run_id)

    def get_threads(self, run_id: UUID) -> list[Thread]:
        return self._for_run(self.threads, run_id)

    def get_episode_entities(self, run_id: UUID) -> list[EpisodeEntity]:
        return self._for_run(self.episode_entities, run_id)

    def get_episode_topics(self, run_id: UUID) -> list[EpisodeTopic]:
        return self._for_run(self.episode_topics, run_id)

    def get_topic_relations(self, run_id: UUID) -> list[TopicRelation]:
        return self._for_run(self.topic_relations, run_id)

    def get_thread_episodes(self, run_id: UUID) -> list[ThreadEpisode]:
        return self._for_run(self.thread_episodes, run_id)

    @staticmethod
    def _write(store: dict[UUID, object], values: Sequence[object], key: str) -> None:
        for value in values:
            store[getattr(value, key)] = value

    @staticmethod
    def _for_run(store: dict[UUID, object], run_id: UUID) -> list:
        return [value for value in store.values() if value.organizer_run_id == run_id]

    def _update_run(
        self,
        run_id: UUID,
        finished_at: datetime,
        status: OrganizerRunStatus,
        error: str | None,
    ) -> None:
        run = self.runs[run_id]
        self.runs[run_id] = run.model_copy(
            update={"finished_at": finished_at, "status": status, "error": error}
        )
