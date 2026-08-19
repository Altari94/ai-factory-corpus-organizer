"""Validate one operator-selected real-corpus organizer run without reading raw files.

Usage (after setting the server-only Supabase environment variables):
    python scripts/validate_real_corpus_e2e.py <organizer-run-id> <source-id> <source-id> [...]
"""

import sys
from uuid import UUID

from app.adapters.semantic_factory import build_supabase_semantic_adapters
from app.config.settings import get_settings
from app.services.e2e_gate import EndToEndAcceptanceGate


def main(arguments: list[str]) -> None:
    if len(arguments) < 3:
        raise SystemExit("usage: validate_real_corpus_e2e.py <organizer-run-id> <source-id> <source-id> [...]")
    run_id = UUID(arguments[0])
    expected_source_ids = {UUID(value) for value in arguments[1:]}
    adapters = build_supabase_semantic_adapters(get_settings())
    rows = adapters.semantic.client.table("episodes").select("start_unit_id,end_unit_id").eq("organizer_run_id", str(run_id)).execute().data
    unit_ids = {row["start_unit_id"] for row in rows} | {row["end_unit_id"] for row in rows}
    canonical_rows = adapters.semantic.client.table("content_units").select("unit_id,canonical_documents(source_id)").in_("unit_id", list(unit_ids)).execute().data
    unit_to_source = {
        UUID(row["unit_id"]): UUID(row["canonical_documents"]["source_id"])
        for row in canonical_rows
        if row.get("canonical_documents")
    }
    report = EndToEndAcceptanceGate(adapters.semantic).validate(
        run_id,
        canonical_unit_to_source=unit_to_source,
        expected_source_ids=expected_source_ids,
    )
    print(report.model_dump(mode="json"))
    if not report.accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
