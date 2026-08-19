from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.semantic import (
    Entity,
    Episode,
    EpisodeEntity,
    EpisodeRelation,
    EpisodeStatus,
    EpisodeTopic,
    OrganizerRun,
    OrganizerRunStatus,
    Thread,
    ThreadEpisode,
    Topic,
    TopicRelation,
)


CORPUS_ID = UUID("e4bc5ac3-86d5-4b29-bf53-d100df30a1ab")
DOCUMENT_ID = UUID("a0cfcdf3-3daf-4e95-ae0b-a0dc9f2a05f4")


def make_run(*, algorithm_version: str = "1.0.0") -> OrganizerRun:
    return OrganizerRun(
        organizer_run_id=uuid4(),
        corpus_id=CORPUS_ID,
        code_version="abc123",
        algorithm_version=algorithm_version,
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        status=OrganizerRunStatus.SUCCEEDED,
    )


def test_every_derived_object_carries_run_provenance() -> None:
    run = make_run()
    episode_id = uuid4()
    entity_id = uuid4()
    topic_id = uuid4()
    child_topic_id = uuid4()
    thread_id = uuid4()
    derived = [
        Episode(
            organizer_run_id=run.organizer_run_id,
            episode_id=episode_id,
            document_id=DOCUMENT_ID,
            start_unit_id=uuid4(),
            end_unit_id=uuid4(),
            sequence=0,
            confidence=0.8,
            status=EpisodeStatus.CONFIRMED,
        ),
        Entity(organizer_run_id=run.organizer_run_id, entity_id=entity_id, canonical_name="Kiel"),
        Topic(organizer_run_id=run.organizer_run_id, topic_id=topic_id, label="Organisation"),
        EpisodeRelation(
            organizer_run_id=run.organizer_run_id,
            relation_id=uuid4(),
            from_episode_id=episode_id,
            to_episode_id=uuid4(),
            relation_type="FOLLOWS",
        ),
        Thread(organizer_run_id=run.organizer_run_id, thread_id=thread_id, label="Planung"),
        EpisodeEntity(
            organizer_run_id=run.organizer_run_id,
            link_id=uuid4(),
            episode_id=episode_id,
            entity_id=entity_id,
        ),
        EpisodeTopic(
            organizer_run_id=run.organizer_run_id,
            link_id=uuid4(),
            episode_id=episode_id,
            topic_id=topic_id,
        ),
        TopicRelation(
            organizer_run_id=run.organizer_run_id,
            relation_id=uuid4(),
            parent_topic_id=topic_id,
            child_topic_id=child_topic_id,
        ),
        ThreadEpisode(
            organizer_run_id=run.organizer_run_id,
            link_id=uuid4(),
            thread_id=thread_id,
            episode_id=episode_id,
            sequence=0,
        ),
    ]

    assert all(item.organizer_run_id == run.organizer_run_id for item in derived)


def test_episode_references_canonical_units_and_preserves_chronology() -> None:
    run = make_run()
    start_unit_id = uuid4()
    end_unit_id = uuid4()
    episode = Episode(
        organizer_run_id=run.organizer_run_id,
        episode_id=uuid4(),
        document_id=DOCUMENT_ID,
        start_unit_id=start_unit_id,
        end_unit_id=end_unit_id,
        sequence=3,
    )

    assert episode.start_unit_id == start_unit_id
    assert episode.end_unit_id == end_unit_id
    assert episode.sequence == 3
    assert "text" not in Episode.model_fields


def test_topics_entities_threads_and_many_to_many_links_are_distinct() -> None:
    run = make_run()
    episode_a = uuid4()
    episode_b = uuid4()
    topic = Topic(
        organizer_run_id=run.organizer_run_id,
        topic_id=uuid4(),
        label="Sicherheit",
        parent_topic_id=uuid4(),
    )
    entity = Entity(
        organizer_run_id=run.organizer_run_id,
        entity_id=uuid4(),
        canonical_name="Feuerwehr",
    )
    thread = Thread(
        organizer_run_id=run.organizer_run_id,
        thread_id=uuid4(),
        label="Ablaufplanung",
    )
    topic_links = [
        EpisodeTopic(
            organizer_run_id=run.organizer_run_id,
            link_id=uuid4(),
            episode_id=episode_a,
            topic_id=topic.topic_id,
        ),
        EpisodeTopic(
            organizer_run_id=run.organizer_run_id,
            link_id=uuid4(),
            episode_id=episode_b,
            topic_id=topic.topic_id,
        ),
    ]
    cross_source_thread_links = [
        ThreadEpisode(
            organizer_run_id=run.organizer_run_id,
            link_id=uuid4(),
            thread_id=thread.thread_id,
            episode_id=episode_a,
            sequence=0,
        ),
        ThreadEpisode(
            organizer_run_id=run.organizer_run_id,
            link_id=uuid4(),
            thread_id=thread.thread_id,
            episode_id=episode_b,
            sequence=1,
        ),
    ]

    assert type(topic) is not type(entity) is not type(thread)
    assert len(topic_links) == 2
    assert [link.sequence for link in cross_source_thread_links] == [0, 1]


def test_runs_are_immutable_history_and_comparable_by_version() -> None:
    first = make_run(algorithm_version="1.0.0")
    second = make_run(algorithm_version="2.0.0")

    assert first.organizer_run_id != second.organizer_run_id
    assert first.algorithm_version != second.algorithm_version
    assert first.model_dump() != second.model_dump()
    assert first.status == OrganizerRunStatus.SUCCEEDED
    assert second.status == OrganizerRunStatus.SUCCEEDED
