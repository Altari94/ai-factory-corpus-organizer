"""F0.3 adapter for the CanonicalReadPort.

This module is infrastructure only. F0.4 application services depend on the
port and never on this adapter or on Supabase table names.
"""

from uuid import UUID

from supabase import Client

from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit, RunStatus
from app.ports.canonical_read import CanonicalReadPort


class SupabaseCanonicalReadAdapter(CanonicalReadPort):
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_current_successful_run(self, source_id: UUID, schema_version: str | None = None) -> CanonicalRun | None:
        rows = self.client.table("processing_runs").select("*").eq("source_id", str(source_id)).eq("status", "SUCCEEDED").order("finished_at", desc=True).limit(20).execute().data
        runs = [self._run(row) for row in rows if schema_version is None or _compatible_major(str(row.get("schema_version", "")), schema_version)]
        return runs[0] if runs else None

    def get_document(self, document_id: UUID) -> CanonicalDocument | None:
        rows = self.client.table("canonical_documents").select("*").eq("document_id", str(document_id)).limit(1).execute().data
        if not rows:
            return None
        row = rows[0]
        return CanonicalDocument(document_id=UUID(str(row["document_id"])), source_id=UUID(str(row["source_id"])), document_type=str(row.get("document_type") or "UNKNOWN"), title=row.get("title") or row.get("filename") or row.get("name"))

    def get_unit(self, unit_id: UUID) -> CanonicalUnit | None:
        rows = self.client.table("content_units").select("*").eq("unit_id", str(unit_id)).limit(1).execute().data
        return self._unit(rows[0]) if rows else None

    def get_units_by_ids(self, unit_ids: list[UUID]) -> list[CanonicalUnit]:
        if not unit_ids:
            return []
        result: list[CanonicalUnit] = []
        # Keep PostgREST query URLs bounded for real corpora with many evidence IDs.
        for start in range(0, len(unit_ids), 100):
            batch = unit_ids[start:start + 100]
            rows = self.client.table("content_units").select("*").in_("unit_id", [str(unit_id) for unit_id in batch]).execute().data
            result.extend(self._unit(row) for row in rows)
        return result

    def get_units(self, processing_run_id: UUID) -> list[CanonicalUnit]:
        rows = self.client.table("content_units").select("*").eq("processing_run_id", str(processing_run_id)).order("sequence").execute().data
        return sorted((self._unit(row) for row in rows), key=lambda unit: (unit.sequence, str(unit.unit_id)))

    def get_children(self, parent_unit_id: UUID) -> list[CanonicalUnit]:
        rows = self.client.table("content_units").select("*").eq("parent_unit_id", str(parent_unit_id)).order("sequence").execute().data
        return sorted((self._unit(row) for row in rows), key=lambda unit: (unit.sequence, str(unit.unit_id)))

    @staticmethod
    def _run(row: dict) -> CanonicalRun:
        return CanonicalRun(run_id=UUID(str(row["run_id"])), source_id=UUID(str(row["source_id"])), schema_version=str(row.get("schema_version") or "0.0.0"), status=RunStatus(str(row["status"])), started_at=row.get("started_at"), finished_at=row.get("finished_at"))

    @staticmethod
    def _unit(row: dict) -> CanonicalUnit:
        return CanonicalUnit(unit_id=UUID(str(row["unit_id"])), document_id=UUID(str(row["document_id"])), processing_run_id=UUID(str(row["processing_run_id"])), unit_type=str(row.get("unit_type") or "UNKNOWN"), sequence=int(row.get("sequence", 0)), text=str(row.get("text") or ""), parent_unit_id=UUID(str(row["parent_unit_id"])) if row.get("parent_unit_id") else None, source_native_id=row.get("source_native_id"), original_timestamp=row.get("original_timestamp") or row.get("occurred_at"), speaker=row.get("speaker"), role=row.get("role"), source_locator=row.get("source_locator"))


def _compatible_major(actual: str, requested: str) -> bool:
    return actual.split(".", 1)[0] == requested.split(".", 1)[0]
