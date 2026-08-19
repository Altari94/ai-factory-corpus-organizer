from uuid import UUID

from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit, RunStatus


class InMemoryCanonicalAdapter:
    """Test adapter that exposes the same read contract as the future F0.3 adapter."""

    def __init__(
        self,
        runs: list[CanonicalRun] | None = None,
        documents: list[CanonicalDocument] | None = None,
        units: list[CanonicalUnit] | None = None,
    ) -> None:
        self.runs = runs or []
        self.documents = documents or []
        self.units = units or []

    def get_current_successful_run(
        self, source_id: UUID, schema_version: str | None = None
    ) -> CanonicalRun | None:
        successful = [
            run
            for run in self.runs
            if run.source_id == source_id
            and run.status == RunStatus.SUCCEEDED
            and _compatible_major(run.schema_version, schema_version)
        ]
        return max(successful, key=lambda run: run.started_at) if successful else None

    def get_document(self, document_id: UUID) -> CanonicalDocument | None:
        return next((doc for doc in self.documents if doc.document_id == document_id), None)

    def get_units(self, processing_run_id: UUID) -> list[CanonicalUnit]:
        return sorted(
            [unit for unit in self.units if unit.processing_run_id == processing_run_id],
            key=lambda unit: (unit.sequence, str(unit.unit_id)),
        )

    def get_children(self, parent_unit_id: UUID) -> list[CanonicalUnit]:
        return sorted(
            [unit for unit in self.units if unit.parent_unit_id == parent_unit_id],
            key=lambda unit: (unit.sequence, str(unit.unit_id)),
        )


def _compatible_major(actual: str, requested: str | None) -> bool:
    return requested is None or actual.split(".", 1)[0] == requested.split(".", 1)[0]
