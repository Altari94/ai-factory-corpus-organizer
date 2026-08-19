from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.domain.semantic import Episode, OrganizerRun, OrganizerRunStatus
from app.ports.semantic import SemanticReadPort, SemanticWritePort


def test_in_memory_adapter_satisfies_semantic_ports_and_preserves_runs() -> None:
    adapter = InMemorySemanticAdapter()
    assert isinstance(adapter, SemanticReadPort)
    assert isinstance(adapter, SemanticWritePort)

    run_id = uuid4()
    run = OrganizerRun(
        organizer_run_id=run_id,
        corpus_id=UUID("e4bc5ac3-86d5-4b29-bf53-d100df30a1ab"),
        code_version="test",
        algorithm_version="1.0.0",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
    )
    adapter.create_run(run)
    adapter.complete_run(run_id, datetime.now(timezone.utc))

    assert adapter.get_run(run_id) is not None
    assert adapter.get_run(run_id).status == OrganizerRunStatus.SUCCEEDED


def test_semantic_objects_are_scoped_to_their_run() -> None:
    adapter = InMemorySemanticAdapter()
    run_a = OrganizerRun(
        organizer_run_id=uuid4(),
        corpus_id=uuid4(),
        code_version="a",
        algorithm_version="1.0.0",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
    )
    run_b = run_a.model_copy(update={"organizer_run_id": uuid4(), "code_version": "b"})
    adapter.create_run(run_a)
    adapter.create_run(run_b)
    episode = Episode(
        organizer_run_id=run_a.organizer_run_id,
        episode_id=uuid4(),
        document_id=uuid4(),
        start_unit_id=uuid4(),
        end_unit_id=uuid4(),
        sequence=0,
    )
    adapter.write_episodes([episode])

    assert adapter.get_episodes(run_a.organizer_run_id) == [episode]
    assert adapter.get_episodes(run_b.organizer_run_id) == []
