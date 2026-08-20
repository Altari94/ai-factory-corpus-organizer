from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.domain.semantic import Episode, EpisodeStatus, OrganizerRun, Topic
from app.services.semantic_snapshot import SemanticSnapshotBuilder


def test_snapshot_projects_semantic_objects_without_storage_details() -> None:
    run_id, corpus_id, episode_id, document_id, unit_id, topic_id = (uuid4() for _ in range(6))
    adapter = InMemorySemanticAdapter()
    adapter.create_run(OrganizerRun(organizer_run_id=run_id, corpus_id=corpus_id, code_version="test", algorithm_version="test", semantic_schema_version="1.0.0", started_at=datetime.now(timezone.utc)))
    adapter.write_episodes([Episode(organizer_run_id=run_id, episode_id=episode_id, document_id=document_id, start_unit_id=unit_id, end_unit_id=unit_id, sequence=0, status=EpisodeStatus.CONFIRMED)])
    adapter.write_topics([Topic(organizer_run_id=run_id, topic_id=topic_id, label="Palworld")])
    snapshot = SemanticSnapshotBuilder(adapter).build(run_id)
    assert snapshot.organizer_run_id == run_id
    assert snapshot.episodes[0].evidence_unit_ids == [unit_id, unit_id]
    assert snapshot.topics[0].label == "Palworld"
