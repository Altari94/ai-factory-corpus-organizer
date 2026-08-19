from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.domain.semantic import (
    Entity,
    Episode,
    EpisodeEntity,
    EpisodeRelation,
    EpisodeStatus,
    EpisodeTopic,
    OrganizerRun,
    Thread,
    ThreadEpisode,
    Topic,
)
from app.services.catalogue_builder import CatalogueBuilder, CatalogueNotFoundError


def test_catalogue_exposes_topics_and_corpus_statistics() -> None:
    store = InMemorySemanticAdapter()
    run = OrganizerRun(
        organizer_run_id=uuid4(), corpus_id=uuid4(), code_version="test",
        algorithm_version="test", semantic_schema_version="1.0.0", started_at=datetime.now(timezone.utc),
    )
    first, second = [uuid4(), uuid4()]
    document_id = uuid4()
    episodes = [
        Episode(organizer_run_id=run.organizer_run_id, episode_id=first, document_id=document_id, start_unit_id=uuid4(), end_unit_id=uuid4(), sequence=0, status=EpisodeStatus.CONFIRMED),
        Episode(organizer_run_id=run.organizer_run_id, episode_id=second, document_id=document_id, start_unit_id=uuid4(), end_unit_id=uuid4(), sequence=1, status=EpisodeStatus.CONFIRMED),
    ]
    topic = Topic(organizer_run_id=run.organizer_run_id, topic_id=uuid4(), label="AI Factory", description="Semantic processing")
    entity = Entity(organizer_run_id=run.organizer_run_id, entity_id=uuid4(), canonical_name="Supabase")
    thread = Thread(organizer_run_id=run.organizer_run_id, thread_id=uuid4(), label="Factory thread")
    store.create_run(run)
    store.write_episodes(episodes)
    store.write_topics([topic])
    store.write_entities([entity])
    store.write_episode_topics([EpisodeTopic(organizer_run_id=run.organizer_run_id, link_id=uuid4(), episode_id=first, topic_id=topic.topic_id)])
    store.write_episode_entities([EpisodeEntity(organizer_run_id=run.organizer_run_id, link_id=uuid4(), episode_id=first, entity_id=entity.entity_id, evidence_unit_ids=[episodes[0].start_unit_id])])
    store.write_threads([thread])
    store.write_thread_episodes([ThreadEpisode(organizer_run_id=run.organizer_run_id, link_id=uuid4(), thread_id=thread.thread_id, episode_id=first, sequence=0)])
    store.write_episode_relations([EpisodeRelation(organizer_run_id=run.organizer_run_id, relation_id=uuid4(), from_episode_id=first, to_episode_id=second, relation_type="RELATED", confidence=0.8)])

    catalogue = CatalogueBuilder(store).build(run.organizer_run_id)

    assert catalogue.topics[0].label == "AI Factory"
    assert catalogue.topics[0].episode_count == 1
    assert catalogue.topics[0].entity_ids == [entity.entity_id]
    assert catalogue.statistics.episode_count == 2
    assert catalogue.statistics.unassigned_episode_count == 1
    assert catalogue.statistics.singleton_topic_count == 1


def test_catalogue_rejects_unknown_run() -> None:
    with pytest.raises(CatalogueNotFoundError):
        CatalogueBuilder(InMemorySemanticAdapter()).build(uuid4())
