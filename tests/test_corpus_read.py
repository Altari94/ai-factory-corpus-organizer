from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.in_memory_canonical import InMemoryCanonicalAdapter
from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit, RunStatus
from app.domain.episode_detection import EpisodeMembership
from app.domain.semantic import Episode, EpisodeStatus, EpisodeTopic, OrganizerRun, Topic, TopicRelation
from app.services.corpus_read import CorpusReadService


def test_corpus_read_topic_subtree_preserves_order_and_provenance():
    run_id, source_id, document_id, processing_id = uuid4(), uuid4(), uuid4(), uuid4()
    topic_id, child_id, episode_id = uuid4(), uuid4(), uuid4()
    unit_a, unit_b = uuid4(), uuid4()
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    semantic = InMemorySemanticAdapter()
    semantic.create_run(OrganizerRun(organizer_run_id=run_id, corpus_id=uuid4(), code_version="test", algorithm_version="test", semantic_schema_version="1.0.0", started_at=now))
    semantic.write_topics([Topic(organizer_run_id=run_id, topic_id=topic_id, label="Palworld"), Topic(organizer_run_id=run_id, topic_id=child_id, label="Wirtschaft", parent_topic_id=topic_id)])
    semantic.write_episodes([Episode(organizer_run_id=run_id, episode_id=episode_id, document_id=document_id, start_unit_id=unit_a, end_unit_id=unit_b, sequence=0, status=EpisodeStatus.CONFIRMED)])
    semantic.write_episode_memberships([EpisodeMembership(organizer_run_id=run_id, episode_id=episode_id, canonical_unit_id=unit_a, sequence=0), EpisodeMembership(organizer_run_id=run_id, episode_id=episode_id, canonical_unit_id=unit_b, sequence=1)])
    semantic.write_episode_topics([EpisodeTopic(organizer_run_id=run_id, link_id=uuid4(), episode_id=episode_id, topic_id=child_id)])
    canonical = InMemoryCanonicalAdapter(
        runs=[CanonicalRun(run_id=processing_id, source_id=source_id, schema_version="1.0.0", status=RunStatus.SUCCEEDED, started_at=now)],
        documents=[CanonicalDocument(document_id=document_id, source_id=source_id, document_type="CHAT", title="Palworld")],
        units=[CanonicalUnit(unit_id=unit_a, document_id=document_id, processing_run_id=processing_id, unit_type="MESSAGE", sequence=0, text="first", role="user"), CanonicalUnit(unit_id=unit_b, document_id=document_id, processing_run_id=processing_id, unit_type="MESSAGE", sequence=1, text="second", role="assistant")],
    )
    service = CorpusReadService(semantic, canonical)
    result = service.get_corpus_slice(run_id, topic_id, include_descendants=True)
    assert [item.original_text for item in result.episodes[0].content_units] == ["first", "second"]
    assert result.included_topic_ids == [topic_id, child_id]
    assert result.episodes[0].provenance[0].source_id == source_id
