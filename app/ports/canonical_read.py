from typing import Protocol
from uuid import UUID

from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit


class CanonicalReadPort(Protocol):
    """Stable read contract between F0.3 and the Corpus Organizer."""

    def get_current_successful_run(
        self, source_id: UUID, schema_version: str | None = None
    ) -> CanonicalRun | None: ...

    def get_document(self, document_id: UUID) -> CanonicalDocument | None: ...

    def get_unit(self, unit_id: UUID) -> CanonicalUnit | None: ...

    def get_units(self, processing_run_id: UUID) -> list[CanonicalUnit]: ...

    def get_children(self, parent_unit_id: UUID) -> list[CanonicalUnit]: ...
