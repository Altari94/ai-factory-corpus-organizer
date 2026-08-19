from uuid import UUID

from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit
from app.ports.canonical_read import CanonicalReadPort


class CorpusReader:
    """Application service that reads canonical data only through the port."""

    def __init__(self, canonical_reader: CanonicalReadPort) -> None:
        self.canonical_reader = canonical_reader

    def load_source(
        self, source_id: UUID, schema_version: str | None = None
    ) -> tuple[CanonicalRun, CanonicalDocument, list[CanonicalUnit]] | None:
        run = self.canonical_reader.get_current_successful_run(source_id, schema_version)
        if run is None:
            return None

        units = self.canonical_reader.get_units(run.run_id)
        if not units:
            return None

        document = self.canonical_reader.get_document(units[0].document_id)
        if document is None:
            return None
        return run, document, units
