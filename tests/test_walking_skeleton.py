from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.adapters.in_memory_canonical import InMemoryCanonicalAdapter
from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit, RunStatus
from app.domain.semantic import OrganizerRun
from app.services.walking_skeleton import CorpusLoader, TrivialEpisodeDetector, WalkingSkeletonPipeline


def make_source(source_id: UUID, *, status: RunStatus, document_type: str):
    run_id = uuid4()
    document_id = uuid4()
    run = CanonicalRun(
        run_id=run_id,
        source_id=source_id,
        schema_version="1.0.0",
        status=status,
        started_at=datetime.now(timezone.utc),
    )
    document = CanonicalDocument(
        document_id=document_id,
        source_id=source_id,
        document_type=document_type,
    )
    units = [
        CanonicalUnit(
            unit_id=uuid4(),
            document_id=document_id,
            processing_run_id=run_id,
            unit_type="MESSAGE",
            sequence=0,
            text=f"Message aus {document_type}",
        ),
        CanonicalUnit(
            unit_id=uuid4(),
            document_id=document_id,
            processing_run_id=run_id,
            unit_type="SENTENCE",
            sequence=0,
            text="Message aus dem Canonical Contract.",
        ),
    ]
    return run, document, units


def test_corpus_loader_uses_multiple_successful_compatible_sources() -> None:
    source_a = UUID("f2c9506e-c6dd-47e7-8413-5c665e985f10")
    source_b = UUID("3b7e8a6a-44f3-4659-a7b6-bc0f58d1e2a6")
    failed_source = UUID("2e7a8b77-8d1a-4aaf-87b2-94636c11c26a")
    run_a, doc_a, units_a = make_source(source_a, status=RunStatus.SUCCEEDED, document_type="CHATGPT_MARKDOWN")
    run_b, doc_b, units_b = make_source(source_b, status=RunStatus.SUCCEEDED, document_type="CHATGPT_JSON")
    failed_run, failed_doc, failed_units = make_source(
        failed_source, status=RunStatus.FAILED, document_type="CHATGPT_MARKDOWN"
    )
    adapter = InMemoryCanonicalAdapter(
        [run_a, run_b, failed_run],
        [doc_a, doc_b, failed_doc],
        units_a + units_b + failed_units,
    )

    loaded = CorpusLoader(adapter).load([source_a, source_b, failed_source], "1.2.0")

    assert [item.document.document_type for item in loaded] == [
        "CHATGPT_MARKDOWN",
        "CHATGPT_JSON",
    ]
    assert all(item.run.status == RunStatus.SUCCEEDED for item in loaded)
    assert all(item.units[0].source_native_id is None for item in loaded)


def test_trivial_episode_detector_preserves_unit_provenance() -> None:
    source_id = UUID("f2c9506e-c6dd-47e7-8413-5c665e985f10")
    run, document, units = make_source(
        source_id, status=RunStatus.SUCCEEDED, document_type="CHATGPT_MARKDOWN"
    )
    loaded = CorpusLoader(InMemoryCanonicalAdapter([run], [document], units)).load([source_id])
    organizer_run = OrganizerRun(
        organizer_run_id=uuid4(),
        corpus_id=uuid4(),
        code_version="walking-skeleton",
        algorithm_version="trivial-episode-detector-1.0.0",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
    )

    episodes = TrivialEpisodeDetector().detect(organizer_run, loaded)

    assert len(episodes) == 1
    assert episodes[0].organizer_run_id == organizer_run.organizer_run_id
    assert episodes[0].document_id == document.document_id
    assert episodes[0].start_unit_id == episodes[0].end_unit_id == units[0].unit_id
    assert episodes[0].sequence == units[0].sequence


def test_walking_skeleton_persists_the_complete_path() -> None:
    source_id = UUID("f2c9506e-c6dd-47e7-8413-5c665e985f10")
    run, document, units = make_source(
        source_id, status=RunStatus.SUCCEEDED, document_type="CHATGPT_JSON"
    )
    canonical = InMemoryCanonicalAdapter([run], [document], units)
    from app.adapters.in_memory_semantic import InMemorySemanticAdapter

    semantic = InMemorySemanticAdapter()
    organizer_run = OrganizerRun(
        organizer_run_id=uuid4(),
        corpus_id=uuid4(),
        code_version="walking-skeleton",
        algorithm_version="trivial-episode-detector-1.0.0",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
    )

    episodes = WalkingSkeletonPipeline(canonical, semantic).run(
        organizer_run, [source_id], "1.0.0"
    )

    assert semantic.get_run(organizer_run.organizer_run_id).status == "SUCCEEDED"
    assert semantic.get_episodes(organizer_run.organizer_run_id) == episodes
    assert episodes[0].document_id == document.document_id
