from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from supabase import Client

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


class SupabaseSemanticAdapter:
    """Supabase adapter; database concerns stay outside the domain package."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def create_run(self, run: OrganizerRun) -> None:
        self.client.table("organizer_runs").insert(_dump(run)).execute()

    def write_episodes(self, episodes: Sequence[Episode]) -> None:
        self._insert("episodes", episodes)

    def write_entities(self, entities: Sequence[Entity]) -> None:
        self._insert("entities", entities)

    def write_topics(self, topics: Sequence[Topic]) -> None:
        self._insert("topics", topics)

    def write_episode_relations(self, relations: Sequence[EpisodeRelation]) -> None:
        self._insert("episode_relations", relations)

    def write_threads(self, threads: Sequence[Thread]) -> None:
        self._insert("threads", threads)

    def write_episode_entities(self, links: Sequence[EpisodeEntity]) -> None:
        self._insert("episode_entities", links)

    def write_episode_topics(self, links: Sequence[EpisodeTopic]) -> None:
        self._insert("episode_topics", links)

    def write_topic_relations(self, relations: Sequence[TopicRelation]) -> None:
        self._insert("topic_relations", relations)

    def write_thread_episodes(self, links: Sequence[ThreadEpisode]) -> None:
        self._insert("thread_episodes", links)

    def complete_run(self, run_id: UUID, finished_at: datetime) -> None:
        self._update_run(run_id, {"finished_at": finished_at.isoformat(), "status": "SUCCEEDED", "error": None})

    def fail_run(self, run_id: UUID, finished_at: datetime, error: str) -> None:
        self._update_run(run_id, {"finished_at": finished_at.isoformat(), "status": "FAILED", "error": error})

    def get_run(self, run_id: UUID) -> OrganizerRun | None:
        response = self.client.table("organizer_runs").select("*").eq("organizer_run_id", str(run_id)).limit(1).execute()
        return OrganizerRun.model_validate(response.data[0]) if response.data else None

    def get_episodes(self, run_id: UUID) -> list[Episode]:
        return self._read("episodes", run_id, Episode)

    def get_entities(self, run_id: UUID) -> list[Entity]:
        return self._read("entities", run_id, Entity)

    def get_topics(self, run_id: UUID) -> list[Topic]:
        return self._read("topics", run_id, Topic)

    def get_episode_relations(self, run_id: UUID) -> list[EpisodeRelation]:
        return self._read("episode_relations", run_id, EpisodeRelation)

    def get_threads(self, run_id: UUID) -> list[Thread]:
        return self._read("threads", run_id, Thread)

    def get_episode_entities(self, run_id: UUID) -> list[EpisodeEntity]:
        return self._read("episode_entities", run_id, EpisodeEntity)

    def get_episode_topics(self, run_id: UUID) -> list[EpisodeTopic]:
        return self._read("episode_topics", run_id, EpisodeTopic)

    def get_topic_relations(self, run_id: UUID) -> list[TopicRelation]:
        return self._read("topic_relations", run_id, TopicRelation)

    def get_thread_episodes(self, run_id: UUID) -> list[ThreadEpisode]:
        return self._read("thread_episodes", run_id, ThreadEpisode)

    def _insert(self, table: str, values: Sequence[object]) -> None:
        if values:
            self.client.table(table).insert([_dump(value) for value in values]).execute()

    def _update_run(self, run_id: UUID, values: dict) -> None:
        self.client.table("organizer_runs").update(values).eq("organizer_run_id", str(run_id)).execute()

    def _read(self, table: str, run_id: UUID, model: type):
        response = self.client.table(table).select("*").eq("organizer_run_id", str(run_id)).execute()
        return [model.model_validate(row) for row in response.data]


def _dump(value: object) -> dict:
    data = value.model_dump(mode="json")
    if isinstance(value, OrganizerRun):
        data["organizer_run_id"] = str(value.organizer_run_id)
    return data
