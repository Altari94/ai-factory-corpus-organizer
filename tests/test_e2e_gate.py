from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.domain.semantic import (
    Episode, EpisodeEntity, EpisodeRelation, EpisodeStatus, EpisodeTopic,
    OrganizerRun, OrganizerRunStatus, Thread, ThreadEpisode, Topic,
)
from app.services.e2e_gate import EndToEndAcceptanceGate


def test_e2e_gate_checks_source_provenance_evidence_topics_and_threads() -> None:
    store = InMemorySemanticAdapter()
    run_id, source_a, source_b, document_id = uuid4(), uuid4(), uuid4(), uuid4()
    first_unit, second_unit = uuid4(), uuid4()
    first_episode, second_episode = uuid4(), uuid4()
    store.create_run(OrganizerRun(organizer_run_id=run_id, corpus_id=uuid4(), code_version="test", algorithm_version="test", semantic_schema_version="1.0", started_at=datetime.now(timezone.utc), status=OrganizerRunStatus.SUCCEEDED))
    store.write_episodes([
        Episode(organizer_run_id=run_id, episode_id=first_episode, document_id=document_id, start_unit_id=first_unit, end_unit_id=first_unit, sequence=0, status=EpisodeStatus.CONFIRMED),
        Episode(organizer_run_id=run_id, episode_id=second_episode, document_id=document_id, start_unit_id=second_unit, end_unit_id=second_unit, sequence=1, status=EpisodeStatus.CONFIRMED),
    ])
    topic = Topic(organizer_run_id=run_id, topic_id=uuid4(), label="Topic")
    thread = Thread(organizer_run_id=run_id, thread_id=uuid4(), label="Thread")
    store.write_topics([topic])
    store.write_episode_topics([EpisodeTopic(organizer_run_id=run_id, link_id=uuid4(), episode_id=first_episode, topic_id=topic.topic_id)])
    store.write_episode_relations([EpisodeRelation(organizer_run_id=run_id, relation_id=uuid4(), from_episode_id=first_episode, to_episode_id=second_episode, relation_type="SAME_THREAD", evidence_unit_ids=[first_unit, second_unit])])
    store.write_episode_entities([EpisodeEntity(organizer_run_id=run_id, link_id=uuid4(), episode_id=first_episode, entity_id=uuid4(), evidence_unit_ids=[first_unit])])
    store.write_threads([thread])
    store.write_thread_episodes([ThreadEpisode(organizer_run_id=run_id, link_id=uuid4(), thread_id=thread.thread_id, episode_id=first_episode, sequence=0)])

    report = EndToEndAcceptanceGate(store).validate(run_id, canonical_unit_to_source={first_unit: source_a, second_unit: source_b}, expected_source_ids={source_a, source_b})

    assert report.accepted is True
