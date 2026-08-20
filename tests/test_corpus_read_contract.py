from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.in_memory_canonical import InMemoryCanonicalAdapter
from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.adapters.supabase_canonical import SupabaseCanonicalReadAdapter
from app.adapters.supabase_semantic import SupabaseSemanticAdapter
from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit, RunStatus
from app.domain.episode_detection import EpisodeMembership
from app.domain.semantic import Episode, EpisodeStatus, EpisodeTopic, OrganizerRun, Topic
from app.services.corpus_read import CorpusReadService
from tests.test_semantic_adapter_contract import FakeClient


def _fixture():
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    run_id, corpus_id, source_id, processing_id, document_id = (uuid4() for _ in range(5))
    topic_id, child_id, episode_id = (uuid4() for _ in range(3))
    unit_a, unit_b = uuid4(), uuid4()
    run = OrganizerRun(organizer_run_id=run_id, corpus_id=corpus_id, code_version="contract", algorithm_version="1", semantic_schema_version="1.0.0", started_at=now)
    topics = [Topic(organizer_run_id=run_id, topic_id=topic_id, label="Parent"), Topic(organizer_run_id=run_id, topic_id=child_id, label="Child", parent_topic_id=topic_id)]
    episode = Episode(organizer_run_id=run_id, episode_id=episode_id, document_id=document_id, start_unit_id=unit_a, end_unit_id=unit_b, sequence=0, status=EpisodeStatus.CONFIRMED)
    memberships = [EpisodeMembership(organizer_run_id=run_id, episode_id=episode_id, canonical_unit_id=unit_a, sequence=0), EpisodeMembership(organizer_run_id=run_id, episode_id=episode_id, canonical_unit_id=unit_b, sequence=1)]
    links = [EpisodeTopic(organizer_run_id=run_id, link_id=uuid4(), episode_id=episode_id, topic_id=child_id)]
    canonical = (CanonicalRun(run_id=processing_id, source_id=source_id, schema_version="1.0.0", status=RunStatus.SUCCEEDED, started_at=now), CanonicalDocument(document_id=document_id, source_id=source_id, document_type="CHAT", title="Contract source"), [CanonicalUnit(unit_id=unit_a, document_id=document_id, processing_run_id=processing_id, unit_type="MESSAGE", sequence=0, text="original one"), CanonicalUnit(unit_id=unit_b, document_id=document_id, processing_run_id=processing_id, unit_type="MESSAGE", sequence=1, text="original two")])
    return run, topics, [episode], memberships, links, canonical


def _populate(adapter, run, topics, episodes, memberships, links):
    adapter.create_run(run)
    adapter.write_topics(topics)
    adapter.write_episodes(episodes)
    adapter.write_episode_memberships(memberships)
    adapter.write_episode_topics(links)
    adapter.complete_run(run.organizer_run_id, datetime.now(timezone.utc))


def test_same_corpus_read_contract_for_inmemory_and_supabase_adapters():
    run, topics, episodes, memberships, links, canonical_data = _fixture()
    memory_semantic = InMemorySemanticAdapter()
    _populate(memory_semantic, run, topics, episodes, memberships, links)
    memory_canonical = InMemoryCanonicalAdapter([canonical_data[0]], [canonical_data[1]], canonical_data[2])
    memory_result = CorpusReadService(memory_semantic, memory_canonical).get_corpus_slice(run.organizer_run_id, topics[0].topic_id)

    fake = FakeClient()
    supabase_semantic = SupabaseSemanticAdapter(fake)
    _populate(supabase_semantic, run, topics, episodes, memberships, links)
    fake.database["processing_runs"] = [{"run_id": str(canonical_data[0].run_id), "source_id": str(canonical_data[0].source_id), "schema_version": "1.0.0", "status": "SUCCEEDED", "started_at": canonical_data[0].started_at.isoformat()}]
    fake.database["canonical_documents"] = [canonical_data[1].model_dump(mode="json")]
    fake.database["content_units"] = [unit.model_dump(mode="json") for unit in canonical_data[2]]
    supabase_result = CorpusReadService(supabase_semantic, SupabaseCanonicalReadAdapter(fake)).get_corpus_slice(run.organizer_run_id, topics[0].topic_id)

    assert [item.original_text for item in memory_result.episodes[0].content_units] == [item.original_text for item in supabase_result.episodes[0].content_units]
    assert memory_result.included_topic_ids == supabase_result.included_topic_ids
    assert memory_result.episodes[0].provenance == supabase_result.episodes[0].provenance
