from datetime import datetime, timezone
from uuid import uuid4

from app.adapters.in_memory_canonical import InMemoryCanonicalAdapter
from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit, RunStatus
from app.domain.episode_detection import EpisodeMembership
from app.domain.semantic import Episode, EpisodeStatus, OrganizerRun
from app.services.integrity import OrganizerIntegrityService


def test_integrity_service_checks_provenance_round_trip():
    now = datetime.now(timezone.utc)
    run_id, source_id, document_id, processing_id, episode_id, unit_id = (uuid4() for _ in range(6))
    semantic = InMemorySemanticAdapter()
    semantic.create_run(OrganizerRun(organizer_run_id=run_id, corpus_id=uuid4(), code_version="test", algorithm_version="test", semantic_schema_version="1.0.0", started_at=now))
    semantic.write_episodes([Episode(organizer_run_id=run_id, episode_id=episode_id, document_id=document_id, start_unit_id=unit_id, end_unit_id=unit_id, sequence=0, status=EpisodeStatus.CONFIRMED)])
    semantic.write_episode_memberships([EpisodeMembership(organizer_run_id=run_id, episode_id=episode_id, canonical_unit_id=unit_id, sequence=0)])
    canonical = InMemoryCanonicalAdapter([CanonicalRun(run_id=processing_id, source_id=source_id, schema_version="1.0.0", status=RunStatus.SUCCEEDED, started_at=now)], [CanonicalDocument(document_id=document_id, source_id=source_id, document_type="CHAT", title="Test")], [CanonicalUnit(unit_id=unit_id, document_id=document_id, processing_run_id=processing_id, unit_type="MESSAGE", sequence=0, text="original")])
    report = OrganizerIntegrityService(semantic, canonical).validate(run_id)
    assert report.passed
    assert any(check.name == "provenance_round_trip" and check.passed for check in report.checks)
