from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.adapters.in_memory_canonical import InMemoryCanonicalAdapter
from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit, RunStatus
from app.services.corpus_reader import CorpusReader


SOURCE_ID = UUID("c8e2fef9-66d5-40bb-ae24-35ab7c6fddf1")
RUN_ID = UUID("9f4f77c2-dc0f-4a25-aac5-5f5304f9cb89")
DOCUMENT_ID = UUID("d5a2f00b-ef24-4d9b-98dc-b3bc5a8c8d01")


def test_in_memory_adapter_reads_canonical_contract() -> None:
    now = datetime.now(timezone.utc)
    run = CanonicalRun(
        run_id=RUN_ID,
        source_id=SOURCE_ID,
        schema_version="1.0.0",
        status=RunStatus.SUCCEEDED,
        started_at=now,
    )
    document = CanonicalDocument(
        document_id=DOCUMENT_ID,
        source_id=SOURCE_ID,
        document_type="CHATGPT_MARKDOWN",
        title="Example",
    )
    unit = CanonicalUnit(
        unit_id=uuid4(),
        document_id=DOCUMENT_ID,
        processing_run_id=RUN_ID,
        unit_type="MESSAGE",
        sequence=0,
        text="Eine Nachricht.",
    )

    reader = CorpusReader(InMemoryCanonicalAdapter([run], [document], [unit]))
    loaded = reader.load_source(SOURCE_ID, "1.2.0")

    assert loaded is not None
    loaded_run, loaded_document, units = loaded
    assert loaded_run.run_id == RUN_ID
    assert loaded_document.document_type == "CHATGPT_MARKDOWN"
    assert units[0].text == "Eine Nachricht."


def test_reader_does_not_depend_on_original_source_format() -> None:
    now = datetime.now(timezone.utc)
    run = CanonicalRun(
        run_id=RUN_ID,
        source_id=SOURCE_ID,
        schema_version="1.0.0",
        status=RunStatus.SUCCEEDED,
        started_at=now,
    )
    document = CanonicalDocument(
        document_id=DOCUMENT_ID,
        source_id=SOURCE_ID,
        document_type="CHATGPT_JSON",
    )
    unit = CanonicalUnit(
        unit_id=uuid4(),
        document_id=DOCUMENT_ID,
        processing_run_id=RUN_ID,
        unit_type="MESSAGE",
        sequence=0,
        text="Dieselbe Canonical-Struktur.",
    )

    loaded = CorpusReader(InMemoryCanonicalAdapter([run], [document], [unit])).load_source(SOURCE_ID)

    assert loaded is not None
    assert loaded[2][0].unit_type == "MESSAGE"
    assert loaded[2][0].text == "Dieselbe Canonical-Struktur."
